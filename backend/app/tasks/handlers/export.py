import io
import json
import re
import zipfile
from dataclasses import dataclass
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

PAGE_WIDTH = 1080
PAGE_MAX_HEIGHT = 1920
MARGIN = 36
GUTTER = 20
HEADER_HEIGHT = 110

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
)


def _load_export_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for candidate in _FONT_CANDIDATES:
        path = Path(candidate)
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), size=size, index=0)
        except OSError:
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    max_width: int,
    *,
    max_lines: int = 6,
) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    lines: list[str] = []
    current = ""
    overflow = False
    for char in cleaned:
        trial = current + char
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        if len(lines) + 1 >= max_lines:
            overflow = True
            break
        if current:
            lines.append(current)
        current = char
    if current and not overflow:
        lines.append(current)
    elif current and overflow:
        lines.append(current)
    if overflow and lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = f"{last}…" if last else "…"
    return lines


def _panel_source(store: LocalObjectStore, panel: PanelRecord) -> Path | None:
    if panel.current_image_asset_id:
        source = store.find_asset_file(str(panel.current_image_asset_id))
        if source is not None and source.is_file():
            return source
    image_name = Path(panel.current_image_url or "").name
    if not image_name:
        return None
    candidate = SAMPLE_DIR / image_name
    return candidate if candidate.is_file() else None


@dataclass(frozen=True)
class _PanelLayout:
    panel: PanelRecord
    index: int
    height: int
    source: Path | None


def _measure_panels(store: LocalObjectStore, panels: list[PanelRecord]) -> list[_PanelLayout]:
    content_width = PAGE_WIDTH - 2 * MARGIN
    layouts: list[_PanelLayout] = []
    for index, panel in enumerate(panels):
        source = _panel_source(store, panel)
        if source is not None:
            with Image.open(source) as image:
                ratio = image.height / max(image.width, 1)
        else:
            ratio = 0.75
        height = max(420, min(960, int(content_width * ratio)))
        layouts.append(_PanelLayout(panel=panel, index=index, height=height, source=source))
    return layouts


def _draw_panel(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    layout: _PanelLayout,
    *,
    x: int,
    y: int,
    content_width: int,
    bubble_font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    meta_font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> None:
    cell_height = layout.height
    if layout.source is not None:
        with Image.open(layout.source) as image:
            fitted = ImageOps.fit(image.convert("RGB"), (content_width, cell_height))
            canvas.paste(fitted, (x, y))
    else:
        draw.rectangle((x, y, x + content_width, y + cell_height), fill="#d4d4d4")
        draw.text(
            (x + 24, y + cell_height // 2 - 12),
            f"第 {layout.index + 1} 格暂无画面",
            fill="#737373",
            font=meta_font,
        )
    draw.rectangle(
        (x, y, x + content_width - 1, y + cell_height - 1),
        outline="#111111",
        width=4,
    )
    dialogue = (layout.panel.dialogue or "").strip()
    if not dialogue:
        return
    pad_x, pad_y = 18, 14
    max_text_width = int(content_width * 0.62) - 2 * pad_x
    lines = _wrap_text(draw, dialogue, bubble_font, max_text_width, max_lines=5)
    if not lines:
        return
    line_height = 36
    text_width = max(int(draw.textlength(line, font=bubble_font)) for line in lines)
    bubble_w = min(content_width - 48, text_width + 2 * pad_x)
    bubble_h = pad_y * 2 + line_height * len(lines)
    bubble_x = x + 24 if layout.index % 2 == 0 else x + content_width - 24 - bubble_w
    bubble_y = y + 24
    draw.rounded_rectangle(
        (bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h),
        radius=18,
        fill="white",
        outline="#111111",
        width=3,
    )
    for line_index, line in enumerate(lines):
        draw.text(
            (bubble_x + pad_x, bubble_y + pad_y + line_index * line_height),
            line,
            fill="#111111",
            font=bubble_font,
        )


def _encode_png(canvas: Image.Image) -> bytes:
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _compose_page(
    title: str,
    layouts: list[_PanelLayout],
    *,
    page_index: int,
    page_count: int,
    total_panels: int,
    include_title: bool,
) -> bytes:
    content_width = PAGE_WIDTH - 2 * MARGIN
    title_font = _load_export_font(40)
    meta_font = _load_export_font(22)
    bubble_font = _load_export_font(28)
    header = HEADER_HEIGHT if include_title else 56
    body_height = sum(item.height for item in layouts) + GUTTER * max(len(layouts) - 1, 0)
    height = MARGIN * 2 + header + body_height
    canvas = Image.new("RGB", (PAGE_WIDTH, height), "#f5f5f5")
    draw = ImageDraw.Draw(canvas)
    if include_title:
        draw.text((MARGIN, MARGIN), title[:64] or "未命名", fill="#171717", font=title_font)
        draw.text(
            (MARGIN, MARGIN + 54),
            f"漫序 · 共 {total_panels} 格 · 第 {page_index}/{page_count} 页",
            fill="#6b7280",
            font=meta_font,
        )
    else:
        draw.text(
            (MARGIN, MARGIN),
            f"第 {page_index}/{page_count} 页",
            fill="#6b7280",
            font=meta_font,
        )
    y = MARGIN + header
    for layout in layouts:
        _draw_panel(
            canvas,
            draw,
            layout,
            x=MARGIN,
            y=y,
            content_width=content_width,
            bubble_font=bubble_font,
            meta_font=meta_font,
        )
        y += layout.height + GUTTER
    return _encode_png(canvas)


def render_png(title: str, panels: list[PanelRecord]) -> bytes:
    """Compose one vertical comic-strip PNG for an episode."""
    if not panels:
        raise ValueError("没有可导出的已确认分镜")
    store = LocalObjectStore()
    layouts = _measure_panels(store, panels)
    return _compose_page(
        title,
        layouts,
        page_index=1,
        page_count=1,
        total_panels=len(panels),
        include_title=True,
    )


def _page_used_height(items: list[_PanelLayout], *, first_page: bool) -> int:
    header = HEADER_HEIGHT if first_page else 56
    if not items:
        return MARGIN * 2 + header
    return MARGIN * 2 + header + sum(item.height for item in items) + GUTTER * (len(items) - 1)


def _pack_pages(layouts: list[_PanelLayout]) -> list[list[_PanelLayout]]:
    """Greedy pack panels into pages under PAGE_MAX_HEIGHT."""
    pages: list[list[_PanelLayout]] = []
    current: list[_PanelLayout] = []
    for layout in layouts:
        first_page = not pages
        trial = [*current, layout]
        if current and _page_used_height(trial, first_page=first_page) > PAGE_MAX_HEIGHT:
            pages.append(current)
            current = [layout]
        else:
            current = trial
    if current:
        pages.append(current)
    return pages


def render_episode_pages(title: str, panels: list[PanelRecord]) -> list[bytes]:
    """Return page-sized PNG bytes for one episode (may be empty if no panels)."""
    if not panels:
        return []
    store = LocalObjectStore()
    layouts = _measure_panels(store, panels)
    pages = _pack_pages(layouts)
    return [
        _compose_page(
            title,
            page_layouts,
            page_index=page_index,
            page_count=len(pages),
            total_panels=len(panels),
            include_title=page_index == 1,
        )
        for page_index, page_layouts in enumerate(pages, start=1)
    ]


def render_png_zip(title: str, panels: list[PanelRecord]) -> bytes:
    """Pack the episode into page-sized PNGs inside a ZIP."""
    pages = render_episode_pages(title, panels)
    if not pages:
        raise ValueError("没有可导出的已确认分镜")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for page_index, png in enumerate(pages, start=1):
            zf.writestr(f"page-{page_index:02d}.png", png)
    return archive.getvalue()


def render_anthology_zip(
    episodes: list[tuple[str, list[PanelRecord]]],
) -> bytes:
    """ZIP with one folder per episode: 01-title/page-01.png …"""
    archive = io.BytesIO()
    wrote = 0
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for episode_index, (title, panels) in enumerate(episodes, start=1):
            pages = render_episode_pages(title, panels)
            if not pages:
                continue
            safe = re.sub(r'[\\/:*?"<>|\r\n]+', "_", (title or "").strip()) or "episode"
            folder = f"{episode_index:02d}-{safe.strip(' .')[:80]}"
            for page_index, png in enumerate(pages, start=1):
                zf.writestr(f"{folder}/page-{page_index:02d}.png", png)
                wrote += 1
    if wrote == 0:
        raise ValueError("所选故事单元没有可导出的分镜画面")
    return archive.getvalue()


def render_anthology_pdf(
    episodes: list[tuple[str, list[PanelRecord]]],
) -> bytes:
    """One multi-page PDF in episode order."""
    images: list[Image.Image] = []
    try:
        for title, panels in episodes:
            for png in render_episode_pages(title, panels):
                images.append(Image.open(io.BytesIO(png)).convert("RGB"))
        if not images:
            raise ValueError("所选故事单元没有可导出的分镜画面")
        buffer = io.BytesIO()
        first, *rest = images
        first.save(buffer, format="PDF", save_all=True, append_images=rest)
        return buffer.getvalue()
    finally:
        for image in images:
            image.close()


def sanitize_export_filename(title: str, extension: str) -> str:
    """Build a download-safe filename that always includes the type suffix."""
    base = re.sub(r'[\\/:*?"<>|\r\n]+', "_", (title or "").strip()) or "storyboard"
    base = base.strip(" .")[:120] or "storyboard"
    suffix = extension if extension.startswith(".") else f".{extension}"
    if base.lower().endswith(suffix.lower()):
        return base[:160]
    return f"{base}{suffix}"[:160]


async def _load_episode_panels(
    session: AsyncSession,
    episode_id: UUID,
    *,
    include_unapproved: bool,
) -> list[PanelRecord]:
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
    return panels


@register(TaskType.EXPORT)
async def handle_export(session: AsyncSession, task: GenerationTaskRecord) -> dict[str, Any]:
    request_data = task.request_data if isinstance(task.request_data, dict) else {}
    include_unapproved = bool(request_data.get("include_unapproved_panels", False))
    export_format = str(request_data["format"])
    export_id = uuid4()
    scope = str(request_data.get("scope") or "episode")
    project_id = UUID(str(request_data.get("project_id") or task.project_id))

    if scope == "anthology":
        from app.db.models import ProjectRecord

        project = await session.get(ProjectRecord, project_id)
        if project is None:
            raise ValueError("项目不存在")
        raw_ids = request_data.get("episode_ids")
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValueError("合集导出需要至少一个故事单元")
        episode_payload: list[tuple[str, list[PanelRecord]]] = []
        for raw_id in raw_ids:
            episode = await session.get(EpisodeRecord, UUID(str(raw_id)))
            if episode is None or episode.project_id != project_id:
                raise ValueError("合集中包含无效故事单元")
            panels = await _load_episode_panels(
                session, episode.id, include_unapproved=include_unapproved
            )
            episode_payload.append((episode.title, panels))
        if export_format == "pdf":
            raw = render_anthology_pdf(episode_payload)
            mime = "application/pdf"
            extension = "pdf"
        else:
            raw = render_anthology_zip(episode_payload)
            mime = "application/zip"
            extension = "zip"
        filename = sanitize_export_filename(f"{project.title}-合集", extension)
        episode_id: UUID | None = None
    else:
        episode_id = UUID(str(request_data["episode_id"]))
        episode = await session.get(EpisodeRecord, episode_id)
        if episode is None:
            raise ValueError("故事单元不存在")
        project_id = episode.project_id
        panels = await _load_episode_panels(
            session, episode_id, include_unapproved=include_unapproved
        )
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
        elif export_format == "png_zip":
            raw = render_png_zip(episode.title, panels)
            mime = "application/zip"
            extension = "zip"
        else:
            raw = render_png(episode.title, panels)
            mime = "image/png"
            extension = "png"
        filename = sanitize_export_filename(episode.title, extension)

    session.add(
        ExportRecord(
            id=export_id,
            project_id=project_id,
            episode_id=episode_id,
            format=export_format,
            filename=filename,
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
