import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import require_rate_limit
from app.core.security import check_csrf, current_account
from app.db.models import (
    CharacterRecord,
    EpisodeRecord,
    ExportRecord,
    GenerationTaskRecord,
    ImageVersionRecord,
    PanelRecord,
    ProjectRecord,
    SceneRecord,
)
from app.db.session import get_session
from app.schemas.workspace import (
    Character,
    CharacterGenerationRequest,
    CharacterPatch,
    Episode,
    EpisodeCreate,
    EpisodePatch,
    ExportRequest,
    GenerationTask,
    PanelImageGenerationRequest,
    PanelImageVersion,
    PanelOrder,
    Project,
    ProjectCreate,
    ProjectPage,
    ProjectPatch,
    Scene,
    SceneGenerationRequest,
    ScenePatch,
    StoryboardGenerationRequest,
    StoryboardPanel,
    StoryboardPanelCreate,
    StoryboardPanelPatch,
)
from app.services.task_queue import enqueue_generation_task

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def require_workspace_account(request: Request, session: SessionDep) -> None:
    account = await current_account(request, session)
    request.state.account_id = account.id
    params = request.path_params
    project_id = params.get("project_id")
    if project_id is None and params.get("episode_id") is not None:
        episode = await session.get(EpisodeRecord, params["episode_id"])
        project_id = episode.project_id if episode else None
    if project_id is None and params.get("panel_id") is not None:
        panel = await session.get(PanelRecord, params["panel_id"])
        episode = await session.get(EpisodeRecord, panel.episode_id) if panel else None
        project_id = episode.project_id if episode else None
    for parameter, model in (("character_id", CharacterRecord), ("scene_id", SceneRecord)):
        if project_id is None and params.get(parameter) is not None:
            resource = await session.get(model, params[parameter])
            project_id = getattr(resource, "project_id", None)
    if project_id is None and params.get("task_id") is not None:
        task = await session.get(GenerationTaskRecord, params["task_id"])
        project_id = task.project_id if task else None
    if project_id is None and params.get("asset_id") is not None:
        export = await session.get(ExportRecord, params["asset_id"])
        if export is not None:
            episode = await session.get(EpisodeRecord, export.episode_id)
            project_id = episode.project_id if episode else None
        else:
            version = await session.scalar(
                select(ImageVersionRecord).where(ImageVersionRecord.asset_id == params["asset_id"])
            )
            panel = await session.get(PanelRecord, version.panel_id) if version else None
            episode = await session.get(EpisodeRecord, panel.episode_id) if panel else None
            project_id = episode.project_id if episode else None
    if project_id is not None:
        project = await session.get(ProjectRecord, project_id)
        if project is None or project.owner_id != account.id:
            raise HTTPException(404, "资源不存在")
    elif any(value is not None for value in params.values()):
        raise HTTPException(404, "资源不存在")


router = APIRouter(
    tags=["Projects", "Episodes", "Characters", "Scenes", "Storyboards", "Generations", "Exports"],
    dependencies=[
        Depends(require_workspace_account),
        Depends(check_csrf),
        Depends(require_rate_limit),
    ],
)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


def _task_view(task: GenerationTaskRecord) -> GenerationTask:
    return GenerationTask.model_validate(task)


def _panel_view(panel: PanelRecord) -> dict[str, object]:
    return {
        "id": panel.id,
        "episode_id": panel.episode_id,
        "position": panel.position,
        "scene_description": panel.scene_description,
        "shot": panel.shot,
        "composition": panel.composition,
        "character_actions": panel.character_actions,
        "emotion": panel.emotion,
        "dialogue": panel.dialogue,
        "story_purpose": panel.story_purpose,
        "image_prompt": panel.image_prompt,
        "character_ids": panel.character_ids,
        "scene_id": panel.scene_id,
        "review_status": panel.review_status,
        "current_image_asset_id": panel.current_image_asset_id,
        "version": panel.version,
        "created_at": panel.created_at,
        "updated_at": panel.updated_at,
    }


async def _create_task(
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    owner_id: UUID,
    project_id: UUID,
    task_type: str,
    request_data: dict[str, object],
    episode_id: UUID | None = None,
    panel_id: UUID | None = None,
    retry_of_task_id: UUID | None = None,
) -> GenerationTask:
    task = GenerationTaskRecord(
        owner_id=owner_id,
        project_id=project_id,
        episode_id=episode_id,
        panel_id=panel_id,
        task_type=task_type,
        status="queued",
        progress=0,
        request_data=request_data,
        retry_of_task_id=retry_of_task_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    try:
        await enqueue_generation_task(task.id)
    except Exception as error:
        raise HTTPException(503, "生成队列暂时不可用，任务已保存并将在服务恢复后重试") from error
    return _task_view(task)


@router.get("/projects", operation_id="listProjects", response_model=ProjectPage)
async def list_projects(
    request: Request,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: UUID | None = None,
) -> ProjectPage:
    query = (
        select(ProjectRecord)
        .where(ProjectRecord.owner_id == request.state.account_id)
        .order_by(ProjectRecord.created_at.desc(), ProjectRecord.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(ProjectRecord.id < cursor)
    rows = list((await session.scalars(query)).all())
    next_cursor = str(rows[limit - 1].id) if len(rows) > limit else None
    return ProjectPage(
        items=[Project.model_validate(row) for row in rows[:limit]], next_cursor=next_cursor
    )


@router.post("/projects", operation_id="createProject", response_model=Project, status_code=201)
async def create_project(body: ProjectCreate, request: Request, session: SessionDep) -> Project:
    record = ProjectRecord(**body.model_dump(), owner_id=request.state.account_id)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return Project.model_validate(record)


@router.get("/projects/{project_id}", operation_id="getProject", response_model=Project)
async def get_project(project_id: UUID, session: SessionDep) -> Project:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise _not_found("项目")
    return Project.model_validate(record)


@router.patch("/projects/{project_id}", operation_id="updateProject", response_model=Project)
async def update_project(project_id: UUID, body: ProjectPatch, session: SessionDep) -> Project:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise _not_found("项目")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return Project.model_validate(record)


@router.delete("/projects/{project_id}", operation_id="deleteProject", status_code=204)
async def delete_project(project_id: UUID, session: SessionDep) -> Response:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise _not_found("项目")
    await session.delete(record)
    await session.commit()
    return Response(status_code=204)


@router.get(
    "/projects/{project_id}/episodes", operation_id="listEpisodes", response_model=list[Episode]
)
async def list_episodes(project_id: UUID, session: SessionDep) -> list[Episode]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    records = await session.scalars(
        select(EpisodeRecord)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position)
    )
    return [Episode.model_validate(record) for record in records]


@router.post(
    "/projects/{project_id}/episodes",
    operation_id="createEpisode",
    response_model=Episode,
    status_code=201,
)
async def create_episode(project_id: UUID, body: EpisodeCreate, session: SessionDep) -> Episode:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    position = await session.scalar(
        select(EpisodeRecord.position)
        .where(EpisodeRecord.project_id == project_id)
        .order_by(EpisodeRecord.position.desc())
        .limit(1)
    )
    record = EpisodeRecord(
        project_id=project_id,
        position=(position + 1 if position is not None else 0),
        **body.model_dump(),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return Episode.model_validate(record)


@router.patch("/episodes/{episode_id}", operation_id="updateEpisode", response_model=Episode)
async def update_episode(episode_id: UUID, body: EpisodePatch, session: SessionDep) -> Episode:
    record = await session.get(EpisodeRecord, episode_id)
    if record is None:
        raise _not_found("故事单元")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return Episode.model_validate(record)


@router.get(
    "/projects/{project_id}/characters",
    operation_id="listCharacters",
    response_model=list[Character],
)
async def list_characters(project_id: UUID, session: SessionDep) -> list[Character]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    rows = await session.scalars(
        select(CharacterRecord).where(CharacterRecord.project_id == project_id)
    )
    return [Character.model_validate(item) for item in rows]


@router.patch(
    "/characters/{character_id}", operation_id="updateCharacter", response_model=Character
)
async def update_character(
    character_id: UUID, body: CharacterPatch, session: SessionDep
) -> Character:
    record = await session.get(CharacterRecord, character_id)
    if record is None:
        raise _not_found("角色")
    values = body.model_dump(exclude_unset=True)
    if "profile" in values and values["profile"] is not None:
        values["profile"] = body.profile.model_dump() if body.profile else None
    for key, value in values.items():
        setattr(record, key, value)
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return Character.model_validate(record)


@router.post(
    "/projects/{project_id}/character-generations",
    operation_id="generateCharacters",
    response_model=GenerationTask,
    status_code=202,
)
async def generate_characters(
    project_id: UUID,
    body: CharacterGenerationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=project_id,
        task_type="character_draft",
        request_data=body.model_dump(mode="json"),
    )


@router.get("/projects/{project_id}/scenes", operation_id="listScenes", response_model=list[Scene])
async def list_scenes(project_id: UUID, session: SessionDep) -> list[Scene]:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    rows = await session.scalars(select(SceneRecord).where(SceneRecord.project_id == project_id))
    return [Scene.model_validate(item) for item in rows]


@router.patch("/scenes/{scene_id}", operation_id="updateScene", response_model=Scene)
async def update_scene(scene_id: UUID, body: ScenePatch, session: SessionDep) -> Scene:
    record = await session.get(SceneRecord, scene_id)
    if record is None:
        raise _not_found("场景")
    values = body.model_dump(exclude_unset=True)
    if "profile" in values and values["profile"] is not None:
        values["profile"] = body.profile.model_dump() if body.profile else None
    for key, value in values.items():
        setattr(record, key, value)
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return Scene.model_validate(record)


@router.post(
    "/projects/{project_id}/scene-generations",
    operation_id="generateScenes",
    response_model=GenerationTask,
    status_code=202,
)
async def generate_scenes(
    project_id: UUID,
    body: SceneGenerationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    if await session.get(ProjectRecord, project_id) is None:
        raise _not_found("项目")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=project_id,
        task_type="scene_draft",
        request_data=body.model_dump(mode="json"),
    )


@router.post(
    "/projects/{project_id}/storyboard-generations",
    operation_id="generateStoryboard",
    response_model=GenerationTask,
    status_code=202,
)
async def generate_storyboard(
    project_id: UUID,
    body: StoryboardGenerationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    episode = await session.get(EpisodeRecord, body.episode_id)
    if episode is None or episode.project_id != project_id:
        raise _not_found("故事单元")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=project_id,
        episode_id=episode.id,
        task_type="storyboard_draft",
        request_data=body.model_dump(mode="json"),
    )


@router.get(
    "/episodes/{episode_id}/panels", operation_id="listPanels", response_model=list[StoryboardPanel]
)
async def list_panels(episode_id: UUID, session: SessionDep) -> list[StoryboardPanel]:
    if await session.get(EpisodeRecord, episode_id) is None:
        raise _not_found("故事单元")
    rows = await session.scalars(
        select(PanelRecord)
        .where(PanelRecord.episode_id == episode_id)
        .order_by(PanelRecord.position)
    )
    return [StoryboardPanel.model_validate(_panel_view(item)) for item in rows]


@router.post(
    "/episodes/{episode_id}/panels",
    operation_id="createPanel",
    response_model=StoryboardPanel,
    status_code=201,
)
async def create_panel(
    episode_id: UUID, body: StoryboardPanelCreate, session: SessionDep
) -> StoryboardPanel:
    if await session.get(EpisodeRecord, episode_id) is None:
        raise _not_found("故事单元")
    position = await session.scalar(
        select(PanelRecord.position)
        .where(PanelRecord.episode_id == episode_id)
        .order_by(PanelRecord.position.desc())
        .limit(1)
    )
    fields = body.model_dump(mode="json", exclude={"id"})
    record = PanelRecord(
        id=body.id or uuid4(),
        episode_id=episode_id,
        position=position + 1 if position is not None else 0,
        **fields,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return StoryboardPanel.model_validate(_panel_view(record))


@router.put(
    "/episodes/{episode_id}/panels/order",
    operation_id="reorderPanels",
    response_model=list[StoryboardPanel],
)
async def reorder_panels(
    episode_id: UUID, body: PanelOrder, session: SessionDep
) -> list[StoryboardPanel]:
    rows = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    if not rows:
        raise _not_found("分镜")
    by_id = {row.id: row for row in rows}
    if len(body.panel_ids) != len(rows) or set(body.panel_ids) != set(by_id):
        raise HTTPException(status_code=409, detail="排序必须包含该故事单元的全部分镜且不能重复")
    for position, row in enumerate(rows):
        row.position = -position - 1
    await session.flush()
    ordered = [by_id[panel_id] for panel_id in body.panel_ids]
    for position, row in enumerate(ordered):
        row.position = position
    await session.commit()
    return [StoryboardPanel.model_validate(_panel_view(row)) for row in ordered]


@router.patch("/panels/{panel_id}", operation_id="updatePanel", response_model=StoryboardPanel)
async def update_panel(
    panel_id: UUID, body: StoryboardPanelPatch, session: SessionDep
) -> StoryboardPanel:
    record = await session.get(PanelRecord, panel_id)
    if record is None:
        raise _not_found("分镜")
    values = body.model_dump(exclude_unset=True, mode="json")
    target_position = values.pop("position", None)
    for key, value in values.items():
        setattr(record, key, value)
    if target_position is not None and target_position != record.position:
        rows = list(
            (
                await session.scalars(
                    select(PanelRecord)
                    .where(PanelRecord.episode_id == record.episode_id)
                    .order_by(PanelRecord.position)
                )
            ).all()
        )
        rows.remove(record)
        rows.insert(min(target_position, len(rows)), record)
        for position, row in enumerate(rows):
            row.position = -position - 1
        await session.flush()
        for position, row in enumerate(rows):
            row.position = position
    record.version += 1
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return StoryboardPanel.model_validate(_panel_view(record))


@router.delete("/panels/{panel_id}", operation_id="deletePanel", status_code=204)
async def delete_panel(panel_id: UUID, session: SessionDep) -> Response:
    record = await session.get(PanelRecord, panel_id)
    if record is None:
        raise _not_found("分镜")
    episode_id = record.episode_id
    rows = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    await session.delete(record)
    await session.flush()
    remaining = [row for row in rows if row.id != panel_id]
    for position, row in enumerate(remaining):
        row.position = -position - 1
    await session.flush()
    for position, row in enumerate(remaining):
        row.position = position
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/panels/{panel_id}/image-generations",
    operation_id="generatePanelImage",
    response_model=GenerationTask,
    status_code=202,
)
async def generate_panel_image(
    panel_id: UUID,
    body: PanelImageGenerationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    panel = await session.get(PanelRecord, panel_id)
    if panel is None:
        raise _not_found("分镜")
    episode = await session.get(EpisodeRecord, panel.episode_id)
    if episode is None:
        raise _not_found("故事单元")
    task_type = "panel_image_edit" if panel.current_image_asset_id else "panel_image"
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=episode.project_id,
        episode_id=episode.id,
        panel_id=panel.id,
        task_type=task_type,
        request_data=body.model_dump(mode="json"),
    )


@router.get(
    "/panels/{panel_id}/image-versions",
    operation_id="listPanelImageVersions",
    response_model=list[PanelImageVersion],
)
async def list_panel_image_versions(panel_id: UUID, session: SessionDep) -> list[PanelImageVersion]:
    panel = await session.get(PanelRecord, panel_id)
    if panel is None:
        raise _not_found("分镜")
    rows = await session.scalars(
        select(ImageVersionRecord)
        .where(ImageVersionRecord.panel_id == panel_id)
        .order_by(ImageVersionRecord.created_at.desc())
    )
    return [
        PanelImageVersion(
            id=item.id,
            panel_id=item.panel_id,
            asset_id=item.asset_id,
            image_url=item.image_url,
            is_current=item.asset_id == panel.current_image_asset_id,
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.put(
    "/panels/{panel_id}/image-versions/{version_id}/selection",
    operation_id="selectPanelImageVersion",
    response_model=PanelImageVersion,
)
async def select_panel_image_version(
    panel_id: UUID, version_id: UUID, session: SessionDep
) -> PanelImageVersion:
    panel = await session.get(PanelRecord, panel_id)
    version = await session.get(ImageVersionRecord, version_id)
    if panel is None or version is None or version.panel_id != panel_id:
        raise _not_found("图像版本")
    panel.current_image_asset_id = version.asset_id
    panel.current_image_url = version.image_url
    panel.version += 1
    await session.commit()
    return PanelImageVersion(
        id=version.id,
        panel_id=panel.id,
        asset_id=version.asset_id,
        image_url=version.image_url,
        is_current=True,
        created_at=version.created_at,
    )


@router.get(
    "/generation-tasks/{task_id}", operation_id="getGenerationTask", response_model=GenerationTask
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
)
async def retry_generation_task(
    task_id: UUID, request: Request, background_tasks: BackgroundTasks, session: SessionDep
) -> GenerationTask:
    previous = await session.get(GenerationTaskRecord, task_id)
    if previous is None:
        raise _not_found("生成任务")
    if previous.status != "failed":
        raise HTTPException(status_code=409, detail="只有失败的任务可以重试")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=previous.project_id,
        episode_id=previous.episode_id,
        panel_id=previous.panel_id,
        task_type=previous.task_type,
        request_data=previous.request_data,
        retry_of_task_id=previous.id,
    )


@router.post(
    "/episodes/{episode_id}/exports",
    operation_id="createEpisodeExport",
    response_model=GenerationTask,
    status_code=202,
)
async def create_episode_export(
    episode_id: UUID,
    body: ExportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> GenerationTask:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise _not_found("故事单元")
    return await _create_task(
        session,
        background_tasks,
        owner_id=request.state.account_id,
        project_id=episode.project_id,
        episode_id=episode.id,
        task_type="export",
        request_data={**body.model_dump(mode="json"), "episode_id": str(episode.id)},
    )


@router.get("/exports/{asset_id}", operation_id="downloadExport")
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


@router.get("/assets/{asset_id}", operation_id="getImageAsset")
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
