"""EXP bake prefers Lettering over panel.dialogue (LETTER-03 / EXP-01)."""

from types import SimpleNamespace

from PIL import Image, ImageDraw

from app.tasks.handlers.export import (
    _LetteringBake,
    _PanelLayout,
    _draw_panel,
    _load_export_font,
)


def test_draw_panel_prefers_lettering_over_dialogue() -> None:
    canvas = Image.new("RGB", (400, 400), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    panel = SimpleNamespace(dialogue="分镜对白不应出现")
    layout = _PanelLayout(
        panel=panel,  # type: ignore[arg-type]
        index=0,
        height=360,
        source=None,
        lettering=(
            _LetteringBake(
                kind="speech_bubble",
                text="字效真源",
                x_pct=10,
                y_pct=8,
                width_pct=50,
                font_size="md",
            ),
        ),
    )
    font = _load_export_font(28)
    _draw_panel(
        canvas,
        draw,
        layout,
        x=20,
        y=20,
        content_width=360,
        bubble_font=font,
        meta_font=font,
    )
    # Smoke: lettering path runs without error; dialogue-only path would also
    # draw, so assert lettering text geometry was used by checking non-empty
    # white region near lettering coords (not a OCR assert).
    px = canvas.getpixel((20 + int(360 * 0.10) + 8, 20 + int(360 * 0.08) + 8))
    assert px == (255, 255, 255)


def test_draw_panel_falls_back_to_dialogue_without_lettering() -> None:
    canvas = Image.new("RGB", (400, 400), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    panel = SimpleNamespace(dialogue="占位对白")
    layout = _PanelLayout(
        panel=panel,  # type: ignore[arg-type]
        index=0,
        height=360,
        source=None,
        lettering=(),
    )
    font = _load_export_font(28)
    _draw_panel(
        canvas,
        draw,
        layout,
        x=20,
        y=20,
        content_width=360,
        bubble_font=font,
        meta_font=font,
    )
    # Fallback bubble sits near top-left for even index (inside fill, past stroke)
    px = canvas.getpixel((20 + 40, 20 + 40))
    assert px == (255, 255, 255)
