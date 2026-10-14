import asyncio
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont, ImageOps
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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
from app.db.session import SessionFactory
from app.services.qwen_image import generate_qwen_image

SAMPLE_DIR = Path(__file__).parents[1] / "static" / "samples"
SAMPLE_IMAGES = ["panel-1.png", "panel-2.png", "panel-3.png", "panel-4.png"]


async def run_generation_task(task_id: UUID) -> None:
    async with SessionFactory() as session:
        task = await session.get(GenerationTaskRecord, task_id)
        if task is None:
            return
        task.status = "running"
        task.progress = 15
        task.updated_at = datetime.now(UTC)
        await session.commit()

    try:
        await asyncio.sleep(0.2)
        async with SessionFactory() as session:
            task = await session.get(GenerationTaskRecord, task_id)
            if task is None:
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
    except Exception as error:
        async with SessionFactory() as session:
            task = await session.get(GenerationTaskRecord, task_id)
            if task is not None:
                task.status = "failed"
                task.error = {"title": "生成任务失败", "detail": str(error)[:500], "status": 500}
                task.updated_at = datetime.now(UTC)
                await session.commit()


async def _process_task(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, object]:
    if task.task_type == "character_draft":
        return await _generate_characters(session, task)
    if task.task_type == "scene_draft":
        return await _generate_scenes(session, task)
    if task.task_type == "storyboard_draft":
        return await _generate_panels(session, task)
    if task.task_type in {"panel_image", "panel_image_edit"}:
        return await _generate_panel_image(session, task)
    if task.task_type == "export":
        return await _create_export(session, task)
    raise ValueError(f"不支持的任务类型：{task.task_type}")


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
    if existing:
        return {"character_ids": [str(item.id) for item in existing]}
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    character = CharacterRecord(
        project_id=project.id,
        name="主角",
        profile={
            "appearance": f"围绕《{project.title}》故事设定的主角外观",
            "outfit": "符合故事题材的标志性服装",
            "personality": "面对核心冲突时展现出鲜明的行动动机",
            "visual_traits": [project.art_style, project.genre],
        },
        status="draft",
        version=1,
    )
    session.add(character)
    await session.flush()
    return {"character_ids": [str(character.id)]}


async def _generate_scenes(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, object]:
    existing = list(
        (
            await session.scalars(
                select(SceneRecord).where(SceneRecord.project_id == task.project_id)
            )
        ).all()
    )
    if existing:
        return {"scene_ids": [str(item.id) for item in existing]}
    project = await session.get(ProjectRecord, task.project_id)
    if project is None:
        raise ValueError("项目不存在")
    scene = SceneRecord(
        project_id=project.id,
        name="主要场景",
        profile={
            "description": f"从故事梗概提取的主要场景：{project.synopsis[:180]}",
            "lighting": "以画风和剧情情绪为依据",
            "palette": project.art_style,
            "visual_traits": [project.genre, "环境设定草稿"],
        },
        status="draft",
        version=1,
    )
    session.add(scene)
    await session.flush()
    return {"scene_ids": [str(scene.id)]}


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
    for item in existing:
        await session.delete(item)
    panels: list[PanelRecord] = []
    beats = [
        ("远景", "建立故事空间，呈现当前冲突。"),
        ("中景", "主角发现异常线索并采取行动。"),
        ("近景", "冲突升级，角色作出关键反应。"),
        ("特写", "留下推动下一段剧情的悬念。"),
    ]
    for position in range(count):
        shot, action = beats[position % len(beats)]
        panel = PanelRecord(
            episode_id=episode_id,
            position=position,
            scene_description=episode.synopsis[:400] or "根据故事梗概展开的场景",
            shot=shot,
            composition=f"第 {position + 1} 格构图：突出当前剧情信息。",
            character_actions=action,
            emotion="紧张、好奇",
            dialogue="",
            story_purpose=f"推进故事节奏与第 {position + 1} 个情节点",
            image_prompt=f"{episode.synopsis[:500]}，{shot}，{action}",
            character_ids=[str(characters[0].id)] if characters else [],
            scene_id=scenes[0].id if scenes else None,
            review_status="draft",
            version=1,
        )
        session.add(panel)
        panels.append(panel)
    await session.flush()
    return {"episode_id": str(episode_id), "panel_ids": [str(panel.id) for panel in panels]}


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
    asset_id = uuid4()
    image_url = await generate_qwen_image(
        api_key=decrypt_secret(config.image_api_key_encrypted),
        model=config.image_model,
        prompt=prompt,
        asset_id=asset_id,
        base_url=config.image_base_url,
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
