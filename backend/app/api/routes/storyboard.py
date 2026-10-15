from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select

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
    panel_view as _panel_view,
)
from app.core.security import (
    require_episode_owner,
    require_panel_owner,
    require_project_owner_dependency,
)
from app.db.models import (
    EpisodeRecord,
    ImageVersionRecord,
    PanelRecord,
)
from app.schemas.workspace import (
    GenerationTask,
    PanelImageGenerationRequest,
    PanelImageVersion,
    PanelOrder,
    StoryboardGenerationRequest,
    StoryboardPanel,
    StoryboardPanelCreate,
    StoryboardPanelPatch,
)

router = create_workspace_router(tags=["Storyboards"])


@router.post(
    "/projects/{project_id}/storyboard-generations",
    operation_id="generateStoryboard",
    response_model=GenerationTask,
    status_code=202,
    dependencies=[Depends(require_project_owner_dependency)],
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
    "/episodes/{episode_id}/panels",
    operation_id="listPanels",
    response_model=list[StoryboardPanel],
    dependencies=[Depends(require_episode_owner)],
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
    dependencies=[Depends(require_episode_owner)],
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
    dependencies=[Depends(require_episode_owner)],
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


@router.patch(
    "/panels/{panel_id}",
    operation_id="updatePanel",
    response_model=StoryboardPanel,
    dependencies=[Depends(require_panel_owner)],
)
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


@router.delete(
    "/panels/{panel_id}",
    operation_id="deletePanel",
    status_code=204,
    dependencies=[Depends(require_panel_owner)],
)
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
    dependencies=[Depends(require_panel_owner)],
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
        idempotency_key=body.idempotency_key,
    )


@router.get(
    "/panels/{panel_id}/image-versions",
    operation_id="listPanelImageVersions",
    response_model=list[PanelImageVersion],
    dependencies=[Depends(require_panel_owner)],
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
    dependencies=[Depends(require_panel_owner)],
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
