import asyncio
import unicodedata
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.logging import api_logger
from app.core.security import decrypt_secret
from app.db.models import (
    CharacterRecord,
    EpisodeRecord,
    GenerationTaskRecord,
    PanelRecord,
    ProjectRecord,
)
from app.providers import generate_image, generate_structured_text
from app.providers.errors import ProviderControlError
from app.tasks.prompts import CHARACTER_DRAFT
from app.tasks.provider_jobs import (
    ImageJobCheckpoint,
    bind_image_job,
    clear_image_job,
    persist_text_checkpoint,
    text_checkpoint,
)
from app.tasks.registry import register
from app.tasks.schemas import CharacterGenerationOutput, GeneratedCharacter
from app.tasks.support import report_progress, require_image_model, require_text_model
from app.tasks.types import TaskType

CastMode = Literal["append", "replace"]


def _normalize_cast_name(name: str) -> str:
    """Lightweight name key: NFKC, strip whitespace, casefold."""
    compact = "".join(unicodedata.normalize("NFKC", name).split())
    return compact.casefold()


def _profile_from_generated(generated: GeneratedCharacter) -> dict[str, object]:
    return {
        "generation_source": "ai",
        "role": generated.role,
        "appearance": generated.appearance,
        "hairstyle": generated.hairstyle,
        "outfit": generated.outfit,
        "signature_traits": generated.signature_traits,
        "personality": generated.personality,
        "visual_traits": [generated.hairstyle, *generated.signature_traits],
        "image_prompt": generated.reference_image_prompt,
    }


def _serialize_session_callback[P](
    lock: asyncio.Lock, callback: Callable[..., Awaitable[P]]
) -> Callable[..., Awaitable[P]]:
    """Serialize provider checkpoint writes that share one AsyncSession."""

    async def locked(*args: object) -> P:
        async with lock:
            return await callback(*args)

    return locked


def _request_data(task: GenerationTaskRecord) -> dict[str, Any]:
    raw = getattr(task, "request_data", None)
    return raw if isinstance(raw, dict) else {}


def _cast_mode(task: GenerationTaskRecord) -> CastMode:
    data = _request_data(task)
    raw = data.get("cast_mode")
    if raw not in ("append", "replace"):
        raw = data.get("character_cast_mode")
    if raw == "replace":
        return "replace"
    return "append"


def _request_uuids(task: GenerationTaskRecord, key: str) -> list[UUID]:
    raw = _request_data(task).get(key)
    if not isinstance(raw, list):
        return []
    ids: list[UUID] = []
    for item in raw:
        try:
            ids.append(UUID(str(item)))
        except ValueError:
            continue
    return ids


async def _scrub_character_ids_from_panels(
    session: AsyncSession, project_id: UUID, removed_ids: set[UUID]
) -> None:
    if not removed_ids:
        return
    removed = {str(item) for item in removed_ids}
    episode_ids = list(
        (
            await session.scalars(
                select(EpisodeRecord.id).where(EpisodeRecord.project_id == project_id)
            )
        ).all()
    )
    if not episode_ids:
        return
    panels = list(
        (
            await session.scalars(
                select(PanelRecord).where(PanelRecord.episode_id.in_(episode_ids))
            )
        ).all()
    )
    for panel in panels:
        current = list(panel.character_ids or [])
        filtered = [item for item in current if item not in removed]
        if filtered != current:
            panel.character_ids = filtered
            try:
                flag_modified(panel, "character_ids")
            except Exception:
                pass


@register(TaskType.CHARACTER_DRAFT)
async def handle_character_draft(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    text_only = bool(_request_data(task).get("text_only"))
    return await generate_characters(session, task, image_only=False, text_only=text_only)


@register(TaskType.CHARACTER_REFERENCE_IMAGES)
async def handle_character_reference_images(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, Any]:
    return await generate_characters(session, task, image_only=True, text_only=False)


async def generate_characters(
    session: AsyncSession,
    task: GenerationTaskRecord,
    *,
    image_only: bool = False,
    text_only: bool = False,
) -> dict[str, Any]:
    if image_only and text_only:
        raise ValueError("image_only 与 text_only 不能同时为 true")
    existing = list(
        (
            await session.scalars(
                select(CharacterRecord).where(CharacterRecord.project_id == task.project_id)
            )
        ).all()
    )
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    requested_ids = _request_uuids(task, "character_ids")
    by_id = {character.id: character for character in existing}
    title, synopsis, genre, art_style = (
        project.title,
        project.synopsis,
        project.genre,
        project.art_style,
    )
    image_api_key: str | None
    image_model: str
    image_base_url: str | None
    locked_preserved_flags: list[bool]
    generated_characters: list[CharacterRecord]

    if image_only:
        config = await require_image_model(session, project.owner_id)
        image_api_key = decrypt_secret(config.image_api_key_encrypted)
        image_model = config.image_model
        image_base_url = config.image_base_url
        if requested_ids:
            generated_characters = [by_id[item] for item in requested_ids if item in by_id]
            if not generated_characters:
                raise ValueError("指定的角色不存在")
        else:
            generated_characters = [
                character for character in existing if character.reference_asset_id is None
            ]
            if not generated_characters:
                raise ValueError("当前项目没有可生成参考图的角色")
        locked_preserved_flags = [
            bool(character.reference_locked and character.reference_asset_id is not None)
            for character in generated_characters
        ]
        await session.commit()
        await report_progress(session, task, 45)
    else:
        config = await require_text_model(session, project.owner_id)
        text_api_key = decrypt_secret(config.text_api_key_encrypted)
        image_api_key = (
            decrypt_secret(config.image_api_key_encrypted)
            if config.image_api_key_encrypted
            else None
        )
        image_model = config.image_model
        image_base_url = config.image_base_url
        text_base_url = config.text_base_url
        text_model = config.text_model
        await session.commit()

        checkpoint = text_checkpoint(task, "characters")
        locked_preserved_flags = []
        if checkpoint is not None:
            checkpoint_ids = [UUID(str(item)) for item in checkpoint.get("character_ids", [])]
            generated_characters = [
                by_id[character_id] for character_id in checkpoint_ids if character_id in by_id
            ]
            if not generated_characters:
                raise ValueError("角色文字设定检查点存在，但角色记录已丢失")
            raw_flags = checkpoint.get("reference_locked_preserved")
            if isinstance(raw_flags, list):
                locked_preserved_flags = [bool(item) for item in raw_flags]
            await report_progress(session, task, 45)
        else:
            await report_progress(session, task, 15)
            targets = (
                [by_id[item] for item in requested_ids if item in by_id] if requested_ids else None
            )
            if requested_ids and not targets:
                raise ValueError("指定的角色不存在")
            guidance = str(_request_data(task).get("guidance", "")).strip()
            guidance_line = f"补充要求：{guidance}\n" if guidance else ""
            cast_mode = _cast_mode(task)
            if targets is not None:
                target_lines = "\n".join(
                    f"- {character.name}（当前身份：{(character.profile or {}).get('role', '')}）"
                    for character in targets
                )
                user_prompt = (
                    f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    f"{guidance_line}"
                    f"请只重新设计下列 {len(targets)} 名角色的完整设定，保持同名角色可辨识：\n"
                    f"{target_lines}\n"
                    f"characters 数组长度必须为 {len(targets)}，并与上列顺序一致。\n"
                    '返回对象格式：{"characters":[{"name":string,"role":string,'
                    '"appearance":string,"hairstyle":string,"outfit":string,'
                    '"signature_traits":[string],"personality":string,'
                    '"reference_image_prompt":string}]}。参考图提示词描述单人全身立绘、'
                    "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
                )
            elif cast_mode == "append" and existing:
                roster_lines = "\n".join(
                    f"- {character.name}（{(character.profile or {}).get('role', '')}）"
                    for character in existing
                )
                user_prompt = (
                    f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    f"{guidance_line}"
                    "作品已有下列角色，请勿返回他们，也不要改写其设定；"
                    "仅在剧情确实需要时补充新人（通常 0 到 3 人；无需新人则返回空数组）：\n"
                    f"{roster_lines}\n"
                    '返回对象格式：{"characters":[{"name":string,"role":string,'
                    '"appearance":string,"hairstyle":string,"outfit":string,'
                    '"signature_traits":[string],"personality":string,'
                    '"reference_image_prompt":string}]}。参考图提示词描述单人全身立绘、'
                    "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
                )
            else:
                user_prompt = (
                    f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                    f"{guidance_line}"
                    "根据剧情设计完整可复用角色阵容（主角、重要配角、必要时反派），"
                    "通常 2 到 6 人，避免只返回单一主角。\n"
                    '返回对象格式：{"characters":[{"name":string,"role":string,'
                    '"appearance":string,"hairstyle":string,"outfit":string,'
                    '"signature_traits":[string],"personality":string,'
                    '"reference_image_prompt":string}]}。参考图提示词描述单人全身立绘、'
                    "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
                )
            output = await generate_structured_text(
                base_url=text_base_url,
                model=text_model,
                api_key=text_api_key,
                system_prompt=CHARACTER_DRAFT.system,
                user_prompt=user_prompt,
                response_model=CharacterGenerationOutput,
            )
            await report_progress(session, task, 35)
            if targets is not None:
                if len(output.characters) != len(targets):
                    raise ValueError("文本模型返回的角色数量不符合请求，请重试")
                generated_characters = []
                for character, generated in zip(targets, output.characters, strict=True):
                    keep_reference = bool(
                        character.reference_locked and character.reference_asset_id is not None
                    )
                    character.name = generated.name
                    character.profile = _profile_from_generated(generated)
                    character.status = "draft"
                    character.version += 1
                    if not keep_reference:
                        character.reference_asset_id = None
                        await clear_image_job(session, task, f"character:{character.id}")
                    locked_preserved_flags.append(keep_reference)
                    generated_characters.append(character)
                await session.flush()
            elif cast_mode == "append":
                by_norm = {
                    _normalize_cast_name(character.name): character for character in existing
                }
                generated_characters = []
                for generated in output.characters:
                    key = _normalize_cast_name(generated.name)
                    if key and key in by_norm:
                        # Same person already in the project cast — never overwrite.
                        continue
                    character = CharacterRecord(
                        project_id=project.id,
                        name=generated.name,
                        profile=_profile_from_generated(generated),
                        status="draft",
                        version=1,
                    )
                    session.add(character)
                    await session.flush()
                    locked_preserved_flags.append(False)
                    generated_characters.append(character)
                    if key:
                        by_norm[key] = character
                await session.flush()
            else:
                generated_characters = []
                for index, generated in enumerate(output.characters):
                    character = (
                        existing[index]
                        if index < len(existing)
                        else CharacterRecord(project_id=project.id, status="draft")
                    )
                    if index >= len(existing):
                        session.add(character)
                    keep_reference = (
                        index < len(existing)
                        and bool(character.reference_locked)
                        and character.reference_asset_id is not None
                    )
                    character.name = generated.name
                    character.profile = _profile_from_generated(generated)
                    character.status = "draft"
                    character.version = character.version + 1 if index < len(existing) else 1
                    if not keep_reference:
                        character.reference_asset_id = None
                    await session.flush()
                    if not keep_reference:
                        await clear_image_job(session, task, f"character:{character.id}")
                    locked_preserved_flags.append(keep_reference)
                    generated_characters.append(character)
                kept_ids = {character.id for character in generated_characters}
                removed_ids = {
                    character.id for character in existing if character.id not in kept_ids
                }
                for character in existing:
                    if character.id in removed_ids:
                        await session.delete(character)
                await _scrub_character_ids_from_panels(session, task.project_id, removed_ids)
                await session.flush()
            await persist_text_checkpoint(
                session,
                task,
                "characters",
                {
                    "character_ids": [str(character.id) for character in generated_characters],
                    "reference_locked_preserved": locked_preserved_flags,
                },
            )
            await report_progress(session, task, 45)

    character_ids = [str(character.id) for character in generated_characters]
    warnings: list[str] = []
    if text_only:
        await report_progress(session, task, 95)
        return {
            "character_ids": character_ids,
            "generation_source": "ai",
            "reference_images_generated": 0,
            "reference_image_generated": False,
            "reference_locked_preserved": any(locked_preserved_flags),
            "warnings": warnings,
            "prompt_template": {"name": CHARACTER_DRAFT.name, "version": CHARACTER_DRAFT.version},
        }

    if not image_api_key:
        warnings.append("角色文字设定已生成；账户尚未配置图像模型密钥，因此没有生成参考图。")
        await report_progress(session, task, 95)
        return {
            "character_ids": character_ids,
            "generation_source": "ai",
            "reference_images_generated": 0,
            "reference_image_generated": False,
            "reference_locked_preserved": any(locked_preserved_flags),
            "warnings": warnings,
            "prompt_template": {"name": CHARACTER_DRAFT.name, "version": CHARACTER_DRAFT.version},
        }

    images_generated = 0
    total = max(len(generated_characters), 1)
    pending: list[tuple[CharacterRecord, ImageJobCheckpoint, str]] = []
    locked_done = 0
    for index, character in enumerate(generated_characters):
        keep_reference = bool(
            character.reference_locked and character.reference_asset_id is not None
        )
        if index < len(locked_preserved_flags):
            keep_reference = locked_preserved_flags[index] or keep_reference
        if keep_reference:
            images_generated += 1
            locked_done += 1
            warnings.append(f"{character.name}文字设定已更新；定妆照已锁定，未替换参考图。")
            continue

        image_prompt = str(character.profile.get("image_prompt", "")).strip()
        image_job = await bind_image_job(session, task, f"character:{character.id}")
        pending.append(
            (
                character,
                image_job,
                (
                    f"{art_style}，{image_prompt}。角色：{character.name}。"
                    "单人全身角色设定图，纯净浅色背景，完整展示发型、服装和标志性特征，"
                    "不得出现文字、标题、边框或水印。"
                ),
            )
        )

    if locked_done:
        await report_progress(session, task, 45 + round(50 * locked_done / total))

    if pending:
        concurrency = max(1, get_settings().image_model_concurrency)
        semaphore = asyncio.Semaphore(concurrency)
        session_lock = asyncio.Lock()
        finished = 0

        async def bump_progress() -> None:
            nonlocal finished
            finished += 1
            await report_progress(session, task, 45 + round(50 * (locked_done + finished) / total))

        async def render_one(
            character: CharacterRecord, image_job: ImageJobCheckpoint, prompt: str
        ) -> None:
            nonlocal images_generated
            async with semaphore:
                try:
                    await generate_image(
                        api_key=image_api_key,
                        model=image_model,
                        prompt=prompt,
                        asset_id=image_job.asset_id,
                        base_url=image_base_url,
                        resume_task_id=image_job.resume_task_id,
                        prompt_extend=False,
                        on_submit_started=_serialize_session_callback(
                            session_lock, image_job.on_submit_started
                        ),
                        on_submit_rejected=_serialize_session_callback(
                            session_lock, image_job.on_submit_rejected
                        ),
                        on_submitted=_serialize_session_callback(
                            session_lock, image_job.on_submitted
                        ),
                    )
                except ProviderControlError:
                    raise
                except ValueError:
                    async with session_lock:
                        warnings.append(
                            f"{character.name}文字设定已生成，但参考图生成失败；"
                            "可在设置中检查图像模型后重试。"
                        )
                        api_logger.warning(
                            "character_reference_generation_failed",
                            extra={
                                "event": "character_reference_generation_failed",
                                "task_id": str(task.id),
                                "character_id": str(character.id),
                                "error_type": "ValueError",
                            },
                        )
                        await bump_progress()
                    return
                async with session_lock:
                    character.reference_asset_id = image_job.asset_id
                    await session.commit()
                    images_generated += 1
                    await bump_progress()

        outcomes = await asyncio.gather(
            *(render_one(character, image_job, prompt) for character, image_job, prompt in pending),
            return_exceptions=True,
        )
        for outcome in outcomes:
            if isinstance(outcome, ProviderControlError):
                raise outcome
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                raise outcome

    return {
        "character_ids": character_ids,
        "generation_source": "ai",
        "reference_images_generated": images_generated,
        "reference_image_generated": images_generated > 0,
        "reference_locked_preserved": any(locked_preserved_flags),
        "warnings": warnings,
        "prompt_template": {"name": CHARACTER_DRAFT.name, "version": CHARACTER_DRAFT.version},
    }
