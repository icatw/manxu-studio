import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm.attributes import flag_modified

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
    GenerationProviderResumeRequest,
    GenerationTask,
)
from app.services.task_queue import enqueue_generation_task
from app.tasks.checkpoints import strip_resumable_checkpoints
from app.tasks.retry_policy import (
    PROVIDER_PROTECTED_ERROR_CODES,
    authorize_provider_resubmit,
    bind_remote_task_id,
    blocks_ordinary_retry,
    has_provider_resume_checkpoint,
    has_saved_remote_task_id,
    requires_resubmit_acknowledgment,
    task_error_code,
)
from app.tasks.runtime import RECOVERY_ATTEMPTS_KEY

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
    if blocks_ordinary_retry(previous.error, previous.request_data):
        code = task_error_code(previous.error) or "unknown"
        raise HTTPException(
            status_code=409,
            detail=(
                f"失败码 {code} 可能已创建远端图像任务，禁止清除检查点的普通重试；"
                "请使用供应商续跑接口绑定远端任务或显式确认重新提交"
            ),
        )
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
    "/generation-tasks/{task_id}/provider-resumes",
    operation_id="resumeProviderGenerationTask",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_task_owner)],
)
async def resume_provider_generation_task(
    task_id: UUID,
    body: GenerationProviderResumeRequest,
    session: SessionDep,
) -> GenerationTask:
    """Requeue the same failed task while preserving provider checkpoints."""
    task = await session.get(GenerationTaskRecord, task_id)
    if task is None:
        raise _not_found("生成任务")
    if task.status != "failed":
        raise HTTPException(status_code=409, detail="只有失败的任务可以续跑")
    request_data = task.request_data if isinstance(task.request_data, dict) else {}
    if not isinstance(task.request_data, dict):
        task.request_data = request_data
    code = task_error_code(task.error)
    if code not in PROVIDER_PROTECTED_ERROR_CODES and not has_provider_resume_checkpoint(
        request_data
    ):
        raise HTTPException(
            status_code=409,
            detail="当前失败不需要供应商续跑，请使用普通重试",
        )

    remote_task_id = (body.remote_task_id or "").strip() or None
    needs_ack = requires_resubmit_acknowledgment(request_data) or (
        code == "PROVIDER_SUBMIT_AMBIGUOUS" and not has_saved_remote_task_id(request_data)
    )
    if remote_task_id:
        try:
            bind_remote_task_id(
                cast(dict[str, Any], request_data),
                remote_task_id=remote_task_id,
                job_key=body.job_key,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
    elif needs_ack and not body.acknowledge_resubmit:
        raise HTTPException(
            status_code=409,
            detail=(
                "提交结果不确定：请提供已确认的 remote_task_id 以续跑，"
                "或设置 acknowledge_resubmit=true 接受可能的重复计费后重新提交"
            ),
        )
    elif needs_ack and body.acknowledge_resubmit:
        try:
            authorize_provider_resubmit(
                request_data,
                job_key=body.job_key,
                include_ready=code == "PROVIDER_SUBMIT_AMBIGUOUS",
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    request_data[RECOVERY_ATTEMPTS_KEY] = 0
    try:
        flag_modified(task, "request_data")
    except Exception:
        pass
    task.status = "queued"
    task.error = None
    task.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(task)
    try:
        await enqueue_generation_task(task.id, reclaim_if_blocked=True)
    except Exception as error:
        raise HTTPException(503, "生成队列暂时不可用，任务已保存并将在服务恢复后重试") from error
    return _task_view(task)


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
