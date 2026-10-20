"""PUBLISH-01 manuscript bake: Lettering only, no dialogue fallback."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw

from app.schemas.workspace import ManuscriptExportRequest
from app.services import generations as generations_service
from app.tasks.handlers.export import (
    _draw_manuscript_slot,
    _LetteringBake,
    _load_export_font,
    _ManuscriptSlot,
    render_manuscript_pdf,
    render_manuscript_png,
    render_manuscript_png_zip,
)


def test_draw_manuscript_slot_bakes_lettering() -> None:
    canvas = Image.new("RGB", (400, 400), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    slot = _ManuscriptSlot(
        index=0,
        height=360,
        gap_after=0,
        source=None,
        lettering=(
            _LetteringBake(
                kind="speech_bubble",
                text="成稿字效",
                x_pct=10,
                y_pct=8,
                width_pct=50,
                font_size="md",
            ),
        ),
    )
    font = _load_export_font(28)
    _draw_manuscript_slot(
        canvas,
        draw,
        slot,
        x=20,
        y=20,
        content_width=360,
        meta_font=font,
    )
    px = canvas.getpixel((20 + int(360 * 0.10) + 8, 20 + int(360 * 0.08) + 8))
    assert px == (255, 255, 255)


def test_draw_manuscript_slot_has_no_dialogue_fallback() -> None:
    """Without Lettering, grey placeholder must not grow a dialogue bubble."""
    canvas = Image.new("RGB", (400, 400), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    slot = _ManuscriptSlot(
        index=0,
        height=360,
        gap_after=0,
        source=None,
        lettering=(),
    )
    font = _load_export_font(28)
    _draw_manuscript_slot(
        canvas,
        draw,
        slot,
        x=20,
        y=20,
        content_width=360,
        meta_font=font,
    )
    # Interior of grey cell (past border) stays neutral grey, not bubble white.
    px = canvas.getpixel((20 + 40, 20 + 40))
    assert px == (212, 212, 212)


def test_render_manuscript_png_and_zip_and_pdf() -> None:
    slots = [
        [
            _ManuscriptSlot(
                index=0,
                height=200,
                gap_after=12,
                source=None,
                lettering=(),
            )
        ],
        [
            _ManuscriptSlot(
                index=1,
                height=180,
                gap_after=0,
                source=None,
                lettering=(
                    _LetteringBake(
                        kind="caption",
                        text="页二旁白",
                        x_pct=12,
                        y_pct=10,
                        width_pct=60,
                        font_size="sm",
                    ),
                ),
            )
        ],
    ]
    png = render_manuscript_png("雾港成稿", slots)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    zipped = render_manuscript_png_zip("雾港成稿", slots)
    assert zipped[:2] == b"PK"
    pdf = render_manuscript_pdf("雾港成稿", slots)
    assert pdf[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_create_manuscript_export_requires_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    episode_id = uuid4()
    owner_id = uuid4()
    project_id = uuid4()

    class FakeSession:
        async def get(self, model, pk):  # noqa: ANN001
            if pk == episode_id:
                return SimpleNamespace(id=episode_id, project_id=project_id, title="本话")
            return None

    async def empty_pages(_session, _episode_id):  # noqa: ANN001
        return []

    monkeypatch.setattr(
        "app.services.layout.list_pages_for_episode",
        empty_pages,
    )

    with pytest.raises(Exception) as raised:
        await generations_service.create_manuscript_export(
            FakeSession(),  # type: ignore[arg-type]
            episode_id=episode_id,
            owner_id=owner_id,
            body=ManuscriptExportRequest(format="png"),
        )
    assert raised.value.status_code == 409
