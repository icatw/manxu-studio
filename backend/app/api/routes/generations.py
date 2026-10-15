import asyncio
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.api.routes.workspace_common import (
    SessionDep,
    create_workspace_router,
)
from app.api.routes.workspace_common import (
    create_task as _create_task,
)
from app.api.routes.workspace_common import (
    not_found as _not_found,
)
from app.api.routes.workspace_common import (
    task_view as _task_view,
)
from app.core.config import get_settings
from app.core.security import (
    require_asset_owner,
    require_episode_owner,
    require_task_owner,
)
from app.db.models import (
    EpisodeRecord,
    ExportRecord,
    GenerationTaskRecord,
)
from app.schemas.workspace import (
    ExportRequest,
    GenerationTask,
)
from app.tasks.checkpoints import strip_resumable_checkpoints

router = create_workspace_router(tags=["Generations", "Exports"])


@router.get(
    "/generation-tasks/{task_id}",
    operation_id="getGenerationTask",
    response_model=GenerationTask,
    dependencies=[Depends(require_task_owner)],
)
async def get_generation_task(task_id: UUID, session: SessionDep) -> GenerationTask:
    task = await session.get(GenerationTaskRecord, task_id)
    if task is None:
        raise _not_found("生成任务")
    return _task_view(task)


@router.post(
    "/generation-tasks/{task_id}/retries",
    operation_id="retryGenerationTask",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_task_owner)],
)
async def retry_generation_task(
    task_id: UUID, request: Request, session: SessionDep
) -> GenerationTask:
    previous = await session.get(GenerationTaskRecord, task_id)
    if previous is None:
        raise _not_found("生成任务")
    if previous.status != "failed":
        raise HTTPException(status_code=409, detail="只有失败的任务可以重试")
    return await _create_task(
        session,
        owner_id=request.state.account_id,
        project_id=previous.project_id,
        episode_id=previous.episode_id,
        panel_id=previous.panel_id,
        task_type=previous.task_type,
        request_data=strip_resumable_checkpoints(previous.request_data),
        retry_of_task_id=previous.id,
    )


@router.post(
    "/episodes/{episode_id}/exports",
    operation_id="createEpisodeExport",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_episode_owner)],
)
async def create_episode_export(
    episode_id: UUID,
    body: ExportRequest,
    request: Request,
    session: SessionDep,
) -> GenerationTask:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise _not_found("故事单元")
    return await _create_task(
        session,
        owner_id=request.state.account_id,
        project_id=episode.project_id,
        episode_id=episode.id,
        task_type="export",
        request_data={**body.model_dump(mode="json"), "episode_id": str(episode.id)},
    )


@router.get(
    "/exports/{asset_id}",
    operation_id="downloadExport",
    dependencies=[Depends(require_asset_owner)],
)
async def download_export(asset_id: UUID, session: SessionDep) -> Response:
    record = await session.get(ExportRecord, asset_id)
    if record is None:
        raise _not_found("导出文件")
    filename = Path(record.filename).name
    content_disposition = f"attachment; filename=export; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=record.content,
        media_type=record.content_type,
        headers={
            "Content-Disposition": content_disposition,
        },
    )


@router.get(
    "/assets/{asset_id}", operation_id="getImageAsset", dependencies=[Depends(require_asset_owner)]
)
async def get_image_asset(asset_id: UUID) -> FileResponse:
    storage = await asyncio.to_thread(Path(get_settings().image_storage_dir).resolve)
    for suffix, media_type in (
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".webp", "image/webp"),
    ):
        path = storage / f"{asset_id}{suffix}"
        if await asyncio.to_thread(path.is_file):
            return FileResponse(
                path,
                media_type=media_type,
                filename=f"{asset_id}{suffix}",
                headers={"Cache-Control": "private, no-store"},
            )
    raise _not_found("图片资源")
