from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import Request, Response

from app.api.routes.auth import logout
from app.core.api_responses import ApiError
from app.core.security import token_hash
from app.db.models import AccountSessionRecord


class LogoutSession:
    def __init__(self, record: SimpleNamespace | None = None) -> None:
        self.record = record
        self.deleted: list[object] = []
        self.committed = False

    async def get(self, model: type[object], record_id: str) -> object | None:
        assert model is AccountSessionRecord
        if self.record and record_id == token_hash("session-token"):
            return self.record
        return None

    async def delete(self, record: object) -> None:
        self.deleted.append(record)

    async def commit(self) -> None:
        self.committed = True


def make_request(cookie: str | None = None, csrf_header: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    if csrf_header:
        headers.append((b"x-csrf-token", csrf_header.encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/auth/logout",
            "raw_path": b"/api/v1/auth/logout",
            "query_string": b"",
            "headers": headers,
            "server": ("test", 80),
            "client": ("test", 1234),
        }
    )


@pytest.mark.parametrize(
    ("cookie", "record"),
    [
        (None, None),
        ("manxu_session=session-token", None),
        (
            "manxu_session=session-token",
            SimpleNamespace(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
        ),
    ],
    ids=["missing-session", "unknown-session", "expired-session"],
)
async def test_logout_clears_cookies_for_missing_unknown_or_expired_session(
    cookie: str | None,
    record: SimpleNamespace | None,
) -> None:
    session = LogoutSession(record)
    response = await logout(
        make_request(cookie), Response(), session
    )

    assert response.status_code == 204
    cookie_headers = [value for name, value in response.raw_headers if name == b"set-cookie"]
    assert any(
        value.startswith(b"manxu_session=") and b"Max-Age=0" in value
        for value in cookie_headers
    )
    assert any(
        value.startswith(b"manxu_csrf=") and b"Max-Age=0" in value
        for value in cookie_headers
    )
    if record:
        assert session.deleted == [record]
        assert session.committed


async def test_logout_requires_csrf_for_active_cookie_session() -> None:
    record = SimpleNamespace(expires_at=datetime.now(UTC) + timedelta(hours=1))
    session = LogoutSession(record)

    with pytest.raises(ApiError) as error:
        await logout(
            make_request("manxu_session=session-token; manxu_csrf=csrf-token"),
            Response(),
            session,
        )

    assert error.value.code == "CSRF_INVALID"
    assert not session.deleted
    assert not session.committed


async def test_logout_revokes_active_cookie_session_with_valid_csrf() -> None:
    record = SimpleNamespace(expires_at=datetime.now(UTC) + timedelta(hours=1))
    session = LogoutSession(record)

    response = await logout(
        make_request(
            "manxu_session=session-token; manxu_csrf=csrf-token", "csrf-token"
        ),
        Response(),
        session,
    )

    assert response.status_code == 204
    assert session.deleted == [record]
    assert session.committed
