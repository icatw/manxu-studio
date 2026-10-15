from types import SimpleNamespace

import pytest

from app.tasks.provider_jobs import bind_image_job
from app.tasks.support import report_progress


@pytest.mark.asyncio
async def test_report_progress_is_monotonic() -> None:
    task = SimpleNamespace(progress=60, updated_at=None)

    class FakeSession:
        async def commit(self) -> None:
            return None

    await report_progress(FakeSession(), task, 40)  # type: ignore[arg-type]
    assert task.progress == 60
    await report_progress(FakeSession(), task, 80)  # type: ignore[arg-type]
    assert task.progress == 80


@pytest.mark.asyncio
async def test_bind_image_job_persists_remote_task_id() -> None:
    task = SimpleNamespace(request_data={})
    commits: list[str] = []

    class FakeSession:
        async def commit(self) -> None:
            commits.append("commit")

    asset_id, resume, on_submitted = await bind_image_job(
        FakeSession(),
        task,
        "scene:abc",  # type: ignore[arg-type]
    )
    assert resume is None
    assert task.request_data["provider_jobs"]["scene:abc"]["asset_id"] == str(asset_id)
    await on_submitted("remote-1")
    assert task.request_data["provider_jobs"]["scene:abc"]["remote_task_id"] == "remote-1"

    asset_id2, resume2, _ = await bind_image_job(
        FakeSession(),
        task,
        "scene:abc",  # type: ignore[arg-type]
    )
    assert asset_id2 == asset_id
    assert resume2 == "remote-1"
    assert len(commits) >= 2
