"""Character and scene application service."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CharacterRecord, ProjectRecord, SceneRecord
from app.schemas.workspace import (
    Character,
    CharacterGenerationRequest,
    CharacterPatch,
    CharacterUpdateResult,
    GenerationTask,
    Scene,
    SceneGenerationRequest,
    ScenePatch,
)
from app.services.change_impact import cast_visual_changed_fields, impact_for_cast
from app.services.generations import create_task


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


def scene_view(record: SceneRecord) -> Scene:
    profile = dict(record.profile)
    profile.pop("name", None)
    return Scene.model_validate(
        {
            "id": record.id,
            "project_id": record.project_id,
            "name": record.name,
            "profile": profile,
            "reference_asset_id": record.reference_asset_id,
            "status": record.status,
            "version": record.version,
        }
    )


async def list_characters(session: AsyncSession, project_id: UUID) -> list[Character]:
    if await session.get(ProjectRecord, project_id) is None:
        raise not_found("项目")
    rows = await session.scalars(
        select(CharacterRecord).where(CharacterRecord.project_id == project_id)
    )
    return [Character.model_validate(item) for item in rows]


async def update_character(
    session: AsyncSession, character_id: UUID, body: CharacterPatch
) -> CharacterUpdateResult:
    record = await session.get(CharacterRecord, character_id)
    if record is None:
        raise not_found("角色")
    visual_fields = cast_visual_changed_fields(record.profile or {}, body)
    values = body.model_dump(exclude_unset=True)
    if "profile" in values and values["profile"] is not None:
        values["profile"] = body.profile.model_dump() if body.profile else None
    for key, value in values.items():
        setattr(record, key, value)
    record.version += 1
    await session.commit()
    await session.refresh(record)
    character = Character.model_validate(record)
    impact = await impact_for_cast(
        session,
        project_id=record.project_id,
        character_id=record.id,
        changed_fields=visual_fields,
    )
    return CharacterUpdateResult(character=character, impact=impact)


async def generate_characters(
    session: AsyncSession, *, project_id: UUID, owner_id: UUID, body: CharacterGenerationRequest
) -> GenerationTask:
    if await session.get(ProjectRecord, project_id) is None:
        raise not_found("项目")
    return await create_task(
        session,
        owner_id=owner_id,
        project_id=project_id,
        task_type="character_reference_images" if body.image_only else "character_draft",
        request_data=body.model_dump(mode="json"),
    )


async def list_scenes(session: AsyncSession, project_id: UUID) -> list[Scene]:
    if await session.get(ProjectRecord, project_id) is None:
        raise not_found("项目")
    rows = await session.scalars(select(SceneRecord).where(SceneRecord.project_id == project_id))
    return [scene_view(item) for item in rows]


async def update_scene(session: AsyncSession, scene_id: UUID, body: ScenePatch) -> Scene:
    record = await session.get(SceneRecord, scene_id)
    if record is None:
        raise not_found("场景")
    values = body.model_dump(exclude_unset=True)
    if "profile" in values and values["profile"] is not None:
        values["profile"] = body.profile.model_dump() if body.profile else None
    for key, value in values.items():
        setattr(record, key, value)
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return scene_view(record)


async def generate_scenes(
    session: AsyncSession, *, project_id: UUID, owner_id: UUID, body: SceneGenerationRequest
) -> GenerationTask:
    if await session.get(ProjectRecord, project_id) is None:
        raise not_found("项目")
    return await create_task(
        session,
        owner_id=owner_id,
        project_id=project_id,
        task_type="scene_reference_images" if body.image_only else "scene_draft",
        request_data=body.model_dump(mode="json"),
    )
