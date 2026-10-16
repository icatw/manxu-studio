from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont

from app.tasks.handlers.export import (
    PAGE_MAX_HEIGHT,
    _load_export_font,
    _pack_pages,
    _PanelLayout,
    _wrap_text,
    render_png,
    render_png_zip,
    sanitize_export_filename,
)


def test_sanitize_export_filename_always_keeps_extension() -> None:
    assert sanitize_export_filename("雾港来信", "png") == "雾港来信.png"
    assert sanitize_export_filename("雾港来信", "zip") == "雾港来信.zip"
    assert sanitize_export_filename("a/b:c", "json").endswith(".json")
    assert sanitize_export_filename("", "png") == "storyboard.png"
    assert sanitize_export_filename("已有.png", "png") == "已有.png"


def test_wrap_text_breaks_cjk_without_spaces() -> None:
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    font = _load_export_font(24)
    lines = _wrap_text(draw, "这是一句比较长的中文对白用来测试换行", font, max_width=120)
    assert len(lines) >= 2
    assert all(lines)


def test_wrap_text_breaks_cjk_with_default_bitmap_font() -> None:
    """CI runners without CJK faces fall back to PIL's bitmap default."""
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    lines = _wrap_text(draw, "这是一句比较长的中文对白用来测试换行", font, max_width=120)
    assert len(lines) >= 2
    assert all(lines)


def test_pack_pages_splits_when_taller_than_budget() -> None:
    panel = SimpleNamespace(dialogue="", current_image_asset_id=None, current_image_url=None)
    tall = [
        _PanelLayout(panel=panel, index=i, height=700, source=None)  # type: ignore[arg-type]
        for i in range(4)
    ]
    pages = _pack_pages(tall)
    assert len(pages) >= 2
    for page in pages:
        assert sum(item.height for item in page) <= PAGE_MAX_HEIGHT


def test_render_png_vertical_comic_includes_title_pixels() -> None:
    panels = [
        SimpleNamespace(
            dialogue="来了吗？",
            current_image_asset_id=None,
            current_image_url=None,
        ),
        SimpleNamespace(
            dialogue="门口有人。",
            current_image_asset_id=None,
            current_image_url=None,
        ),
    ]
    raw = render_png("雾港来信", panels)  # type: ignore[arg-type]
    assert raw.startswith(b"\x89PNG")
    assert len(raw) > 1000


def test_render_png_zip_contains_numbered_pages() -> None:
    panels = [
        SimpleNamespace(
            dialogue=f"对白{index}",
            current_image_asset_id=None,
            current_image_url=None,
        )
        for index in range(6)
    ]
    raw = render_png_zip("雾港来信", panels)  # type: ignore[arg-type]
    with ZipFile(BytesIO(raw)) as archive:
        names = sorted(archive.namelist())
        assert names[0] == "page-01.png"
        assert all(name.endswith(".png") for name in names)
        assert len(names) >= 2
        assert archive.read(names[0]).startswith(b"\x89PNG")


def test_ascii_download_fallback_keeps_suffixes() -> None:
    from app.services.generations import _ascii_export_filename

    assert _ascii_export_filename("雾港来信.png", "image/png") == "export.png"
    assert _ascii_export_filename("notes", "application/json") == "export.json"
    assert _ascii_export_filename("合集.zip", "application/zip") == "export.zip"
    assert _ascii_export_filename("合集.pdf", "application/pdf") == "export.pdf"


def test_anthology_zip_and_pdf_contain_multiple_episodes() -> None:
    from app.tasks.handlers.export import render_anthology_pdf, render_anthology_zip

    ep1 = [
        SimpleNamespace(dialogue="一", current_image_asset_id=None, current_image_url=None),
        SimpleNamespace(dialogue="二", current_image_asset_id=None, current_image_url=None),
    ]
    ep2 = [
        SimpleNamespace(dialogue="三", current_image_asset_id=None, current_image_url=None),
    ]
    payload = [("第一话", ep1), ("第二话", ep2)]
    zipped = render_anthology_zip(payload)  # type: ignore[arg-type]
    with ZipFile(BytesIO(zipped)) as archive:
        names = archive.namelist()
        assert any(name.startswith("01-") and name.endswith(".png") for name in names)
        assert any(name.startswith("02-") and name.endswith(".png") for name in names)
    pdf = render_anthology_pdf(payload)  # type: ignore[arg-type]
    assert pdf.startswith(b"%PDF")
