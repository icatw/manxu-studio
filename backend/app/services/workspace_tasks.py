import asyncio
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import api_logger
from app.core.security import decrypt_secret
from app.db.models import (
    AccountModelConfigRecord,
    CharacterRecord,
    EpisodeRecord,
    ExportRecord,
    GenerationTaskRecord,
    ImageVersionRecord,
    PanelRecord,
    ProjectRecord,
    SceneRecord,
)
from app.db.session import SessionFactory, engine
from app.services.qwen_image import generate_qwen_image
from app.services.text_generation import generate_structured_text

SAMPLE_DIR = Path(__file__).parents[1] / "static" / "samples"
SAMPLE_IMAGES = ["panel-1.png", "panel-2.png", "panel-3.png", "panel-4.png"]


class GeneratedCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=240)
    appearance: str = Field(min_length=1, max_length=2000)
    hairstyle: str = Field(min_length=1, max_length=500)
    outfit: str = Field(min_length=1, max_length=1000)
    signature_traits: list[str] = Field(min_length=1, max_length=8)
    personality: str = Field(min_length=1, max_length=1000)
    reference_image_prompt: str = Field(min_length=1, max_length=3000)


class CharacterGenerationOutput(BaseModel):
    character: GeneratedCharacter


class GeneratedScene(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    lighting: str = Field(min_length=1, max_length=500)
    palette: str = Field(min_length=1, max_length=500)
    visual_traits: list[str] = Field(default_factory=list, max_length=8)


class SceneGenerationOutput(BaseModel):
    scenes: list[GeneratedScene] = Field(min_length=1, max_length=4)


class GeneratedPanel(BaseModel):
    shot: str = Field(min_length=1, max_length=240)
    scene_description: str = Field(min_length=1, max_length=2000)
    composition: str = Field(min_length=1, max_length=1000)
    character_actions: str = Field(min_length=1, max_length=1000)
    emotion: str = Field(min_length=1, max_length=240)
    dialogue: str = Field(default="", max_length=1000)
    story_purpose: str = Field(min_length=1, max_length=1000)
    image_prompt: str = Field(min_length=1, max_length=4000)
    scene_name: str = Field(default="", max_length=120)


class StoryboardGenerationOutput(BaseModel):
    panels: list[GeneratedPanel] = Field(min_length=1, max_length=60)


async def run_generation_task(task_id: UUID) -> None:
    lock_id = int.from_bytes(task_id.bytes[:8], byteorder="big", signed=True)
    async with engine.connect() as lock_connection:
        acquired = await lock_connection.scalar(select(func.pg_try_advisory_lock(lock_id)))
        if not acquired:
            return
        task_type = "unknown"
        try:
            async with SessionFactory() as session:
                task = await session.get(GenerationTaskRecord, task_id)
                if task is None or task.status in {"succeeded", "failed"}:
                    return
                task_type = task.task_type
                project = await session.get(ProjectRecord, task.project_id)
                if project is None or project.owner_id != task.owner_id:
                    task.status = "failed"
                    task.error = {
                        "title": "生成任务失败",
                        "detail": "项目归属已变化",
                        "status": 404,
                    }
                    task.updated_at = datetime.now(UTC)
                    await session.commit()
                    return
                task.status = "running"
                task.progress = 5
                task.updated_at = datetime.now(UTC)
                await session.commit()

            try:
                await asyncio.sleep(0.2)
                async with SessionFactory() as session:
                    task = await session.get(GenerationTaskRecord, task_id)
                    if task is None or task.status != "running":
                        return
                    task.progress = 65
                    task.updated_at = datetime.now(UTC)
                    await session.commit()
                    result = await _process_task(session, task)
                    task = await session.get(GenerationTaskRecord, task_id)
                    if task is None:
                        return
                    task.status = "succeeded"
                    task.progress = 100
                    task.result = result
                    task.error = None
                    task.updated_at = datetime.now(UTC)
                    await session.commit()
            except Exception:
                failure_id = str(uuid4())
                api_logger.exception(
                    "generation_task_failed",
                    extra={
                        "event": "generation_task_failed",
                        "task_id": str(task_id),
                        "failure_id": failure_id,
                        "task_type": task_type,
                    },
                )
                async with SessionFactory() as session:
                    task = await session.get(GenerationTaskRecord, task_id)
                    if task is not None:
                        task_type = task.task_type
                        task.status = "failed"
                        task.error = {
                            "code": (
                                "PROVIDER_ERROR"
                                if task_type.startswith("panel_image")
                                else "TASK_FAILED"
                            ),
                            "message": "图像生成失败，请检查模型配置后重试"
                            if task_type.startswith("panel_image")
                            else "任务执行失败，请稍后重试",
                            "failure_id": failure_id,
                        }
                        task.updated_at = datetime.now(UTC)
                        await session.commit()
        finally:
            await lock_connection.execute(select(func.pg_advisory_unlock(lock_id)))


async def _process_task(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, object]:
    if task.task_type == "character_draft":
        return await _generate_characters(session, task)
    if task.task_type == "scene_draft":
        return await _generate_scenes(session, task)
    if task.task_type == "scene_reference_images":
        return await _generate_scenes(session, task, image_only=True)
    if task.task_type == "storyboard_draft":
        return await _generate_panels(session, task)
    if task.task_type in {"panel_image", "panel_image_edit"}:
        return await _generate_panel_image(session, task)
    if task.task_type == "export":
        return await _create_export(session, task)
    raise ValueError(f"不支持的任务类型：{task.task_type}")


async def _report_progress(
    session: AsyncSession, task: GenerationTaskRecord, progress: int
) -> None:
    task.progress = progress
    task.updated_at = datetime.now(UTC)
    await session.commit()


async def _generate_characters(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, object]:
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
    config = await _configured_model(session, project.owner_id)
    text_api_key = decrypt_secret(config.text_api_key_encrypted)
    image_api_key = (
        decrypt_secret(config.image_api_key_encrypted)
        if config.image_api_key_encrypted
        else None
    )
    image_model = config.image_model
    image_base_url = config.image_base_url
    title, synopsis, genre, art_style = (
        project.title,
        project.synopsis,
        project.genre,
        project.art_style,
    )
    text_base_url = config.text_base_url
    text_model = config.text_model
    await session.commit()
    await _report_progress(session, task, 15)
    output = await generate_structured_text(
        base_url=text_base_url,
        model=text_model,
        api_key=text_api_key,
        system_prompt=(
            "你是专业漫剧编剧和角色设计师。根据用户故事设计一个核心主角，"
            "所有字段必须具体、互相一致，避免泛化套话。只返回符合 JSON schema 的 JSON。"
        ),
        user_prompt=(
            f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
            "返回对象格式：{\"character\": {\"name\": string, \"role\": string, "
            "\"appearance\": string, \"hairstyle\": string, \"outfit\": string, "
            "\"signature_traits\": [string], \"personality\": string, "
            "\"reference_image_prompt\": string}}。参考图提示词描述单人全身立绘、"
            "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
        ),
        response_model=CharacterGenerationOutput,
    )
    generated = output.character
    await _report_progress(session, task, 35)
    profile = {
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
    character = existing[0] if existing else CharacterRecord(project_id=project.id, status="draft")
    if not existing:
        session.add(character)
    character.name = generated.name
    character.profile = cast(dict[str, object], profile)
    character.status = "draft"
    character.version = character.version + 1 if existing else 1
    character.reference_asset_id = None
    await session.flush()
    await session.commit()

    warning: str | None = None
    await _report_progress(session, task, 45)
    if image_api_key:
        asset_id = uuid4()
        try:
            await _report_progress(session, task, 55)
            await generate_qwen_image(
                api_key=image_api_key,
                model=image_model,
                prompt=(
                    f"{art_style}，{generated.reference_image_prompt}。角色：{generated.name}。"
                    "单人全身角色设定图，纯净浅色背景，完整展示发型、服装和标志性特征，"
                    "不得出现文字、标题、边框或水印。"
                ),
                asset_id=asset_id,
                base_url=image_base_url,
            )
            character.reference_asset_id = asset_id
            await session.commit()
            await _report_progress(session, task, 95)
        except Exception as error:
            warning = "角色文字设定已生成，但参考图生成失败；可在设置中检查图像模型后重试。"
            api_logger.warning(
                "character_reference_generation_failed",
                extra={
                    "event": "character_reference_generation_failed",
                    "task_id": str(task.id),
                    "error_type": type(error).__name__,
                },
            )
    else:
        warning = "角色文字设定已生成；账户尚未配置图像模型密钥，因此没有生成参考图。"
    result: dict[str, object] = {
        "character_ids": [str(character.id)],
        "generation_source": "ai",
        "reference_image_generated": bool(character.reference_asset_id),
    }
    if warning:
        result["warnings"] = [warning]
    return result


async def _generate_scenes(
    session: AsyncSession,
    task: GenerationTaskRecord,
    *,
    image_only: bool = False,
) -> dict[str, object]:
    existing = list(
        (
            await session.scalars(
                select(SceneRecord).where(SceneRecord.project_id == task.project_id)
            )
        ).all()
    )
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    episode_id = task.request_data.get("episode_id")
    episode = await session.get(EpisodeRecord, UUID(str(episode_id))) if episode_id else None
    config = (
        await session.get(AccountModelConfigRecord, project.owner_id)
        if image_only
        else await _configured_model(session, project.owner_id)
    )
    if config is None:
        raise ValueError("请先在设置中配置模型")
    if image_only:
        if not existing:
            raise ValueError("当前项目没有可生成参考图的场景")
        generated_scenes = existing
    else:
        text_api_key = decrypt_secret(config.text_api_key_encrypted)
        title, synopsis, genre, art_style = (
            project.title,
            episode.synopsis if episode else project.synopsis,
            project.genre,
            project.art_style,
        )
        guidance = str(task.request_data.get("guidance", ""))
        await session.commit()
        await _report_progress(session, task, 15)
        output = await generate_structured_text(
            base_url=config.text_base_url,
            model=config.text_model,
            api_key=text_api_key,
            system_prompt=(
                "你是漫剧美术设定师。根据剧情设计 1 到 3 个可复用场景资产，"
                "每个场景需有可视化细节、光线和色彩。只返回 JSON。"
            ),
            user_prompt=(
                f"作品：{title}\n梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                f"补充要求：{guidance or '无'}\n返回格式：{{\"scenes\":[{{\"name\":string,"
                "\"description\":string,\"lighting\":string,\"palette\":string,"
                "\"visual_traits\":[string]}}]}。"
            ),
            response_model=SceneGenerationOutput,
        )
        await _report_progress(session, task, 45)
        generated_scenes = []
        for index, generated in enumerate(output.scenes):
            scene = existing[index] if index < len(existing) else SceneRecord(project_id=project.id)
            if index >= len(existing):
                session.add(scene)
            scene.name = generated.name
            scene.profile = cast(dict[str, object], generated.model_dump(exclude={"name"}))
            scene.status = "draft"
            scene.version = scene.version + 1 if index < len(existing) else 1
            await session.flush()
            generated_scenes.append(scene)
        await session.commit()

    scene_ids = [str(scene.id) for scene in generated_scenes]
    warnings: list[str] = []
    image_api_key_encrypted = getattr(config, "image_api_key_encrypted", None)
    if not image_api_key_encrypted:
        warnings.append("场景文字设定已保存；账户尚未配置图像模型 API Key，因此没有生成参考图。")
    else:
        image_api_key = decrypt_secret(image_api_key_encrypted)
        image_model = getattr(config, "image_model", "qwen-image-3.0-pro")
        image_base_url = getattr(config, "image_base_url", None)
        scenes_to_render = [scene for scene in generated_scenes if not scene.reference_asset_id]
        if not image_only:
            await _report_progress(session, task, 55)
        for index, scene in enumerate(scenes_to_render):
            asset_id = uuid4()
            profile = scene.profile
            visual_traits = profile.get("visual_traits", [])
            visual_traits = visual_traits if isinstance(visual_traits, list) else []
            prompt = "\n".join(
                item
                for item in [
                    project.art_style,
                    f"场景：{scene.name}",
                    str(profile.get("description", "")),
                    f"光线：{profile.get('lighting', '')}",
                    f"色彩：{profile.get('palette', '')}",
                    "视觉特征："
                    + "、".join(str(item) for item in visual_traits),
                    "漫剧场景环境概念图，宽幅构图，画面中不出现人物、文字、标注或水印。",
                ]
                if item
            )
            try:
                await session.commit()
                await generate_qwen_image(
                    api_key=image_api_key,
                    model=image_model,
                    prompt=prompt,
                    asset_id=asset_id,
                    base_url=image_base_url,
                )
                scene.reference_asset_id = asset_id
                await session.commit()
            except Exception as error:
                warnings.append(f"{scene.name}参考图生成失败，可稍后单独重试。")
                api_logger.warning(
                    "scene_reference_generation_failed",
                    extra={
                        "event": "scene_reference_generation_failed",
                        "task_id": str(task.id),
                        "scene_id": str(scene.id),
                        "error_type": type(error).__name__,
                    },
                )
            await _report_progress(
                session,
                task,
                55 + round(40 * (index + 1) / max(len(scenes_to_render), 1)),
            )
    return {
        "scene_ids": scene_ids,
        "reference_images_generated": sum(
            bool(scene.reference_asset_id) for scene in generated_scenes
        ),
        "warnings": warnings,
    }


async def _generate_panels(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, object]:
    episode_id = UUID(str(task.request_data["episode_id"]))
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise ValueError("故事单元不存在")
    requested_count = task.request_data.get("panel_count", 4)
    if not isinstance(requested_count, int):
        raise ValueError("分镜数量必须是整数")
    count = requested_count
    characters = list(
        (
            await session.scalars(
                select(CharacterRecord).where(CharacterRecord.project_id == task.project_id)
            )
        ).all()
    )
    scenes = list(
        (
            await session.scalars(
                select(SceneRecord).where(SceneRecord.project_id == task.project_id)
            )
        ).all()
    )
    existing = list(
        (
            await session.scalars(select(PanelRecord).where(PanelRecord.episode_id == episode_id))
        ).all()
    )
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    config = await _configured_model(session, project.owner_id)
    text_api_key = decrypt_secret(config.text_api_key_encrypted)
    title, genre, art_style = project.title, project.genre, project.art_style
    synopsis = episode.synopsis
    character_context = [
        {"name": item.name, **item.profile}
        for item in characters
    ]
    scene_context = [
        {"name": item.name, **item.profile}
        for item in scenes
    ]
    pacing = str(task.request_data.get("pacing", "balanced"))
    await session.commit()
    await _report_progress(session, task, 15)
    output = await generate_structured_text(
        base_url=config.text_base_url,
        model=config.text_model,
        api_key=text_api_key,
        system_prompt=(
            "你是专业漫剧分镜编剧。把故事拆成准确数量的连续镜头，保证因果、动作和情绪连贯，"
            "角色和场景严格沿用给定资产。每格对白可以为空。只返回 JSON。"
        ),
        user_prompt=(
            f"作品：{title}\n题材：{genre}\n画风：{art_style}\n梗概：{synopsis}\n"
            f"分镜数：{count}\n节奏：{pacing}\n角色资产：{character_context}\n场景资产：{scene_context}\n"
            "返回格式：{\"panels\":[{\"shot\":string,\"scene_description\":string,"
            "\"composition\":string,\"character_actions\":string,\"emotion\":string,"
            "\"dialogue\":string,\"story_purpose\":string,\"image_prompt\":string,"
            "\"scene_name\":string}]}。panels 数量必须与分镜数完全一致。"
        ),
        response_model=StoryboardGenerationOutput,
    )
    await _report_progress(session, task, 85)
    if len(output.panels) != count:
        raise ValueError("文本模型返回的分镜数量不符合请求，请重试")
    for item in existing:
        await session.delete(item)
    await session.flush()
    panels: list[PanelRecord] = []
    primary_character_ids = [str(item.id) for item in characters[:1]]
    for position, generated in enumerate(output.panels):
        scene = next((item for item in scenes if item.name == generated.scene_name), None)
        if scene is None and scenes:
            scene = scenes[0]
        panel = PanelRecord(
            episode_id=episode_id,
            position=position,
            scene_description=generated.scene_description,
            shot=generated.shot,
            composition=generated.composition,
            character_actions=generated.character_actions,
            emotion=generated.emotion,
            dialogue=generated.dialogue,
            story_purpose=generated.story_purpose,
            image_prompt=generated.image_prompt,
            character_ids=primary_character_ids,
            scene_id=scene.id if scene else None,
            review_status="draft",
            version=1,
        )
        session.add(panel)
        panels.append(panel)
    await session.flush()
    return {"episode_id": str(episode_id), "panel_ids": [str(panel.id) for panel in panels]}


async def _configured_model(session: AsyncSession, owner_id: UUID) -> AccountModelConfigRecord:
    config = await session.get(AccountModelConfigRecord, owner_id)
    if (
        config is None
        or not config.text_model
        or not config.text_base_url
        or not config.text_api_key_encrypted
    ):
        raise ValueError("请先在设置中保存并测试文本模型配置")
    return config


async def _generate_panel_image(
    session: AsyncSession, task: GenerationTaskRecord
) -> dict[str, object]:
    if task.panel_id is None:
        raise ValueError("缺少目标分镜")
    panel = await session.get(PanelRecord, task.panel_id)
    if panel is None:
        raise ValueError("分镜不存在")
    project = await session.get(ProjectRecord, task.project_id)
    if project is None or project.owner_id is None:
        raise ValueError("项目账户归属缺失")
    config = await session.get(AccountModelConfigRecord, project.owner_id)
    if config is None or not config.image_api_key_encrypted:
        raise ValueError("请先在模型设置中配置 Qwen Image API Key")
    instruction = str(task.request_data.get("instruction", "")).strip()
    prompt = "\n".join(
        item
        for item in [
            project.art_style,
            panel.scene_description,
            panel.shot,
            panel.composition,
            panel.character_actions,
            panel.emotion,
            instruction,
            "无文字、无水印，保持漫画分镜构图",
        ]
        if item
    )
    api_key = decrypt_secret(config.image_api_key_encrypted)
    image_model = config.image_model
    image_base_url = config.image_base_url
    asset_id = uuid4()
    # Release the transaction and database connection before waiting on Qwen.
    await session.commit()
    image_url = await generate_qwen_image(
        api_key=api_key,
        model=image_model,
        prompt=prompt,
        asset_id=asset_id,
        base_url=image_base_url,
    )
    version = ImageVersionRecord(panel_id=panel.id, asset_id=asset_id, image_url=image_url)
    session.add(version)
    panel.current_image_asset_id = asset_id
    panel.current_image_url = image_url
    panel.version += 1
    await session.flush()
    return {"panel_id": str(panel.id), "asset_id": str(asset_id)}


def _load_export_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


async def _create_export(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, object]:
    episode_id = UUID(str(task.request_data["episode_id"]))
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise ValueError("故事单元不存在")
    include_unapproved = bool(task.request_data.get("include_unapproved_panels", False))
    panels = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    if not include_unapproved:
        panels = [panel for panel in panels if panel.review_status == "approved"]
    export_format = str(task.request_data["format"])
    export_id = uuid4()
    if export_format == "production_json":
        content = {
            "episode": {
                "id": str(episode.id),
                "title": episode.title,
                "synopsis": episode.synopsis,
            },
            "panels": [
                {
                    "position": panel.position,
                    "scene_description": panel.scene_description,
                    "shot": panel.shot,
                    "composition": panel.composition,
                    "character_actions": panel.character_actions,
                    "emotion": panel.emotion,
                    "dialogue": panel.dialogue,
                    "story_purpose": panel.story_purpose,
                    "image_prompt": panel.image_prompt,
                    "current_image_url": panel.current_image_url,
                }
                for panel in panels
            ],
        }
        raw = __import__("json").dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
        mime = "application/json"
        extension = "json"
    else:
        raw = _render_png(episode.title, panels)
        mime = "image/png"
        extension = "png"
    session.add(
        ExportRecord(
            id=export_id,
            episode_id=episode_id,
            format=export_format,
            filename=f"{episode.title}.{extension}"[:160],
            content_type=mime,
            content=raw,
        )
    )
    await session.flush()
    return {
        "asset_id": str(export_id),
        "download_url": f"/api/v1/exports/{export_id}",
        "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    }


def _render_png(title: str, panels: list[PanelRecord]) -> bytes:
    if not panels:
        raise ValueError("没有可导出的已确认分镜")
    width = 1600
    margin = 48
    gutter = 24
    columns = 2 if len(panels) > 1 else 1
    cell_width = (width - 2 * margin - gutter * (columns - 1)) // columns
    cell_height = int(cell_width * 0.75)
    rows = (len(panels) + columns - 1) // columns
    header_height = 120
    height = margin * 2 + header_height + rows * cell_height + (rows - 1) * gutter
    canvas = Image.new("RGB", (width, height), "#f4f1ea")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, margin), title[:64], fill="#171717", font=_load_export_font(42))
    draw.text(
        (margin, margin + 60),
        f"漫序 Studio · {len(panels)} 格分镜",
        fill="#65615b",
        font=_load_export_font(22),
    )
    for index, panel in enumerate(panels):
        x = margin + (index % columns) * (cell_width + gutter)
        y = margin + header_height + (index // columns) * (cell_height + gutter)
        asset_id = panel.current_image_asset_id
        source = None
        if asset_id:
            source = next(
                (
                    Path(get_settings().image_storage_dir) / f"{asset_id}{suffix}"
                    for suffix in (".png", ".jpg", ".webp")
                    if (Path(get_settings().image_storage_dir) / f"{asset_id}{suffix}").is_file()
                ),
                None,
            )
        if source is None:
            image_name = Path(panel.current_image_url or "").name
            source = SAMPLE_DIR / image_name
        if source.is_file():
            with Image.open(source) as image:
                canvas.paste(ImageOps.fit(image.convert("RGB"), (cell_width, cell_height)), (x, y))
        else:
            draw.rectangle((x, y, x + cell_width, y + cell_height), fill="#d9d4ca")
        draw.rectangle((x, y, x + cell_width - 1, y + cell_height - 1), outline="#111111", width=5)
        if panel.dialogue:
            bubble_width = min(cell_width - 48, max(280, int(cell_width * 0.68)))
            draw.rounded_rectangle(
                (x + 20, y + 20, x + 20 + bubble_width, y + 76),
                radius=16,
                fill="white",
                outline="#111111",
                width=2,
            )
            draw.text(
                (x + 34, y + 32), panel.dialogue[:36], fill="#111111", font=_load_export_font(20)
            )
        draw.rectangle((x + 8, y + cell_height - 42, x + 54, y + cell_height - 8), fill="#111111")
        draw.text(
            (x + 22, y + cell_height - 40), str(index + 1), fill="white", font=_load_export_font(20)
        )
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
