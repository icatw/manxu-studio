from collections.abc import AsyncIterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import workspace
from app.core.redis import require_rate_limit
from app.db.models import (
    EpisodeRecord,
    GenerationTaskRecord,
    PanelRecord,
    ProjectRecord,
)
from app.db.session import get_session
from app.main import app


class IsolationSession:
    def __init__(self, owner_id: object) -> None:
        self.owner_id = owner_id
        self.project_id = uuid4()
        self.episode_id = uuid4()
        self.panel_id = uuid4()
        self.task_id = uuid4()

    async def get(self, model: type[object], record_id: object) -> object | None:
        if model is ProjectRecord and record_id == self.project_id:
            return SimpleNamespace(id=self.project_id, owner_id=self.owner_id)
        if model is EpisodeRecord and record_id == self.episode_id:
            return SimpleNamespace(id=self.episode_id, project_id=self.project_id)
        if model is PanelRecord and record_id == self.panel_id:
            return SimpleNamespace(id=self.panel_id, episode_id=self.episode_id)
        if model is GenerationTaskRecord and record_id == self.task_id:
            return SimpleNamespace(id=self.task_id, project_id=self.project_id)
        return None

    async def scalars(self, query: object) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: [])


@pytest.mark.parametrize("operation", ["get", "patch", "delete"])
def test_other_account_cannot_read_update_or_delete_project(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    account_a = uuid4()
    account_b = uuid4()
    session = IsolationSession(owner_id=account_b)

    async def signed_in_account(request: object, db: object) -> SimpleNamespace:
        return SimpleNamespace(id=account_a)

    async def override_session() -> AsyncIterator[IsolationSession]:
        yield session

    monkeypatch.setattr(workspace, "current_account", signed_in_account)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            cookies = {"manxu_session": "test", "manxu_csrf": "csrf"}
            headers = {"X-CSRF-Token": "csrf"}
            if operation == "get":
                response = client.get(f"/api/v1/projects/{session.project_id}", cookies=cookies)
            elif operation == "patch":
                response = client.patch(
                    f"/api/v1/projects/{session.project_id}",
                    cookies=cookies,
                    headers=headers,
                    json={"title": "attempt"},
                )
            else:
                response = client.delete(
                    f"/api/v1/projects/{session.project_id}",
                    cookies=cookies,
                    headers=headers,
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    ("path", "record_id"),
    [
        ("/api/v1/episodes/{id}/panels", "episode_id"),
        ("/api/v1/panels/{id}/image-versions", "panel_id"),
        ("/api/v1/generation-tasks/{id}", "task_id"),
    ],
)
def test_other_account_cannot_read_project_children(
    monkeypatch: pytest.MonkeyPatch, path: str, record_id: str
) -> None:
    session = IsolationSession(owner_id=uuid4())

    async def signed_in_account(request: object, db: object) -> SimpleNamespace:
        return SimpleNamespace(id=uuid4())

    async def override_session() -> AsyncIterator[IsolationSession]:
        yield session

    monkeypatch.setattr(workspace, "current_account", signed_in_account)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.get(path.format(id=getattr(session, record_id)))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
