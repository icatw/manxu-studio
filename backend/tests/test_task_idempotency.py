from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import GenerationTaskRecord
from app.services import generations


class _FakeResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def all(self) -> list[object]:
        return [] if self._value is None else [self._value]


class FakeSession:
    def __init__(self, existing: GenerationTaskRecord | None = None) -> None:
        self.existing = existing
        self.added: list[GenerationTaskRecord] = []
        self.flushed = False
        self.committed = False

    async def scalar(self, _query: object) -> GenerationTaskRecord | None:
        return self.existing

    async def get(self, _model: type[object], _record_id: object) -> object | None:
        return SimpleNamespace(model_mode="byok_qwen")

    async def scalars(self, _query: object) -> _FakeResult:
        # Active-task scan for platform concurrency returns empty.
        return _FakeResult(None)

    def add(self, item: GenerationTaskRecord) -> None:
        if getattr(item, "id", None) is None:
            item.id = uuid4()
        if getattr(item, "created_at", None) is None:
            item.created_at = datetime.now(UTC)
        if getattr(item, "updated_at", None) is None:
            item.updated_at = datetime.now(UTC)
        self.added.append(item)

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, item: GenerationTaskRecord) -> None:
        if getattr(item, "id", None) is None:
            item.id = uuid4()
        if getattr(item, "created_at", None) is None:
            item.created_at = datetime.now(UTC)
        if getattr(item, "updated_at", None) is None:
            item.updated_at = datetime.now(UTC)


def _task(*, status: str, key: str = "same-key") -> GenerationTaskRecord:
    now = datetime.now(UTC)
    return GenerationTaskRecord(
        id=uuid4(),
        owner_id=uuid4(),
        project_id=uuid4(),
        episode_id=uuid4(),
        panel_id=uuid4(),
        task_type="panel_image",
        status=status,
        progress=10,
        request_data={},
        idempotency_key=key,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_idempotency_reuses_running_task(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = _task(status="running")
    session = FakeSession(existing)
    enqueued: list[object] = []

    async def enqueue(task_id: object, **_kwargs: object) -> None:
        enqueued.append(task_id)

    monkeypatch.setattr(generations, "enqueue_generation_task", enqueue)

    result = await generations.create_task(
        session,  # type: ignore[arg-type]
        owner_id=existing.owner_id,
        project_id=existing.project_id,
        episode_id=existing.episode_id,
        panel_id=existing.panel_id,
        task_type="panel_image",
        request_data={"instruction": "retry"},
        idempotency_key="same-key",
    )

    assert result.id == existing.id
    assert session.added == []
    assert enqueued == []


@pytest.mark.asyncio
async def test_idempotency_releases_failed_key_and_creates_new(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _task(status="failed")
    session = FakeSession(existing)
    enqueued: list[object] = []

    async def enqueue(task_id: object, **_kwargs: object) -> None:
        enqueued.append(task_id)

    monkeypatch.setattr(generations, "enqueue_generation_task", enqueue)

    result = await generations.create_task(
        session,  # type: ignore[arg-type]
        owner_id=existing.owner_id,
        project_id=existing.project_id,
        episode_id=existing.episode_id,
        panel_id=existing.panel_id,
        task_type="panel_image",
        request_data={"instruction": "retry"},
        idempotency_key="same-key",
    )

    assert existing.idempotency_key is None
    assert session.flushed is True
    assert len(session.added) == 1
    assert session.added[0].idempotency_key == "same-key"
    assert result.id == session.added[0].id
    assert enqueued == [session.added[0].id]


@pytest.mark.asyncio
async def test_create_task_propagates_queue_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()

    async def enqueue(_task_id: object, **_kwargs: object) -> None:
        raise RuntimeError("redis down")

    monkeypatch.setattr(generations, "enqueue_generation_task", enqueue)

    with pytest.raises(HTTPException) as raised:
        await generations.create_task(
            session,  # type: ignore[arg-type]
            owner_id=uuid4(),
            project_id=uuid4(),
            task_type="panel_image",
            request_data={},
        )

    assert raised.value.status_code == 503
    assert session.committed is True
