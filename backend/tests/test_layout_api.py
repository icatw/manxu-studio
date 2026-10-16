"""Layout HTTP ownership and empty-layout access (PAGE A1)."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.redis import require_rate_limit
from app.core.security import current_account_dependency
from app.db.models import (
    EpisodeRecord,
    LayoutPageRecord,
    PageSlotRecord,
    ProjectRecord,
)
from app.db.session import get_session
from app.main import app


class LayoutIsolationSession:
    def __init__(self, owner_id: object) -> None:
        self.owner_id = owner_id
        self.project_id = uuid4()
        self.episode_id = uuid4()
        self.page_id = uuid4()
        self.slot_id = uuid4()

    async def get(self, model: type[object], record_id: object) -> object | None:
        if model is ProjectRecord and record_id == self.project_id:
            return SimpleNamespace(id=self.project_id, owner_id=self.owner_id)
        if model is EpisodeRecord and record_id == self.episode_id:
            return SimpleNamespace(id=self.episode_id, project_id=self.project_id)
        if model is LayoutPageRecord and record_id == self.page_id:
            return SimpleNamespace(id=self.page_id, episode_id=self.episode_id)
        if model is PageSlotRecord and record_id == self.slot_id:
            return SimpleNamespace(id=self.slot_id, page_id=self.page_id)
        return None

    async def scalars(self, query: object) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: [])


def _override(account_id: object, session: LayoutIsolationSession) -> None:
    async def signed_in_account() -> SimpleNamespace:
        return SimpleNamespace(id=account_id)

    async def override_session() -> AsyncIterator[LayoutIsolationSession]:
        yield session

    app.dependency_overrides[current_account_dependency] = signed_in_account
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_rate_limit] = lambda: None


@pytest.mark.parametrize(
    ("method", "path_template", "json_body"),
    [
        ("get", "/api/v1/episodes/{episode_id}/layout", None),
        ("get", "/api/v1/episodes/{episode_id}/layout/preview", None),
        ("post", "/api/v1/episodes/{episode_id}/layout/bootstrap", {}),
        ("post", "/api/v1/episodes/{episode_id}/layout/sync", {}),
        ("put", "/api/v1/episodes/{episode_id}/pages/order", {"page_ids": []}),
        ("put", "/api/v1/pages/{page_id}/slots/order", {"slot_ids": []}),
        ("patch", "/api/v1/slots/{slot_id}", {"height_px": 800}),
    ],
)
def test_other_account_cannot_access_layout(
    method: str,
    path_template: str,
    json_body: dict[str, object] | None,
) -> None:
    owner = uuid4()
    stranger = uuid4()
    session = LayoutIsolationSession(owner_id=owner)
    _override(stranger, session)
    cookies = {"manxu_session": "test", "manxu_csrf": "csrf"}
    headers = {"X-CSRF-Token": "csrf"}
    path = path_template.format(
        episode_id=session.episode_id,
        page_id=session.page_id,
        slot_id=session.slot_id,
    )
    try:
        with TestClient(app) as client:
            request = getattr(client, method)
            if json_body is None:
                response = request(path, cookies=cookies)
            else:
                response = request(path, cookies=cookies, headers=headers, json=json_body)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_owner_can_get_empty_layout() -> None:
    account_id = uuid4()
    session = LayoutIsolationSession(owner_id=account_id)
    _override(account_id, session)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/episodes/{session.episode_id}/layout",
                cookies={"manxu_session": "test"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "OK"
    assert payload["data"]["episode_id"] == str(session.episode_id)
    assert payload["data"]["pages"] == []
    assert payload["data"]["template"] == "vertical_strip"
