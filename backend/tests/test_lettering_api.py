"""Lettering HTTP ownership (LETTER A2)."""

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
    LetteringObjectRecord,
    PageSlotRecord,
    ProjectRecord,
)
from app.db.session import get_session
from app.main import app


class LetteringIsolationSession:
    def __init__(self, owner_id: object) -> None:
        self.owner_id = owner_id
        self.project_id = uuid4()
        self.episode_id = uuid4()
        self.page_id = uuid4()
        self.slot_id = uuid4()
        self.lettering_id = uuid4()

    async def get(self, model: type[object], record_id: object) -> object | None:
        if model is ProjectRecord and record_id == self.project_id:
            return SimpleNamespace(id=self.project_id, owner_id=self.owner_id)
        if model is EpisodeRecord and record_id == self.episode_id:
            return SimpleNamespace(id=self.episode_id, project_id=self.project_id)
        if model is LayoutPageRecord and record_id == self.page_id:
            return SimpleNamespace(id=self.page_id, episode_id=self.episode_id)
        if model is PageSlotRecord and record_id == self.slot_id:
            return SimpleNamespace(id=self.slot_id, page_id=self.page_id)
        if model is LetteringObjectRecord and record_id == self.lettering_id:
            return SimpleNamespace(id=self.lettering_id, slot_id=self.slot_id)
        return None

    async def scalars(self, query: object) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: [])


def _override(account_id: object, session: LetteringIsolationSession) -> None:
    async def signed_in_account() -> SimpleNamespace:
        return SimpleNamespace(id=account_id)

    async def override_session() -> AsyncIterator[LetteringIsolationSession]:
        yield session

    app.dependency_overrides[current_account_dependency] = signed_in_account
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_rate_limit] = lambda: None


@pytest.mark.parametrize(
    ("method", "path_template", "json_body"),
    [
        ("post", "/api/v1/episodes/{episode_id}/layout/lettering/seed", {}),
        (
            "post",
            "/api/v1/slots/{slot_id}/lettering",
            {"kind": "speech_bubble", "text": "你好"},
        ),
        ("patch", "/api/v1/lettering/{lettering_id}", {"text": "改字"}),
        ("delete", "/api/v1/lettering/{lettering_id}", None),
    ],
)
def test_other_account_cannot_access_lettering(
    method: str,
    path_template: str,
    json_body: dict[str, object] | None,
) -> None:
    session = LetteringIsolationSession(owner_id=uuid4())
    _override(uuid4(), session)
    cookies = {"manxu_session": "test", "manxu_csrf": "csrf"}
    headers = {"X-CSRF-Token": "csrf"}
    path = path_template.format(
        episode_id=session.episode_id,
        slot_id=session.slot_id,
        lettering_id=session.lettering_id,
    )
    try:
        with TestClient(app) as client:
            request = getattr(client, method)
            if json_body is None:
                response = request(path, cookies=cookies, headers=headers)
            else:
                response = request(path, cookies=cookies, headers=headers, json=json_body)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
