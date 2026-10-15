import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont, ImageOps
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EpisodeRecord, ExportRecord, GenerationTaskRecord, PanelRecord
from app.providers import LocalObjectStore
from app.tasks.registry import register
from app.tasks.types import TaskType

SAMPLE_DIR = Path(__file__).parents[2] / "static" / "samples"


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


def render_png(title: str, panels: list[PanelRecord]) -> bytes:
    if not panels:
        raise ValueError("没有可导出的已确认分镜")
    store = LocalObjectStore()
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
        source = None
        if panel.current_image_asset_id:
            source = store.find_asset_file(str(panel.current_image_asset_id))
        if source is None:
            image_name = Path(panel.current_image_url or "").name
            candidate = SAMPLE_DIR / image_name
            source = candidate if candidate.is_file() else None
        if source is not None and source.is_file():
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


@register(TaskType.EXPORT)
async def handle_export(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
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
        raw = json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
        mime = "application/json"
        extension = "json"
    else:
        raw = render_png(episode.title, panels)
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
