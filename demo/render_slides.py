#!/usr/bin/env python3
"""Render detailed chapter slides + mux narration with burned-in SRT subtitles."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
WIDTH, HEIGHT = 1920, 1080
BG = (18, 18, 22)
FG = (245, 245, 240)
MUTED = (160, 160, 155)
ACCENT = (220, 90, 70)
CARD = (28, 28, 34)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ):
        try:
            return ImageFont.truetype(path, size=size, index=0)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    fnt: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    line_gap: int = 10,
) -> int:
    """Draw text wrapping by measured width; return y after last line."""
    x, y = xy
    line = ""
    for ch in text:
        trial = line + ch
        bbox = draw.textbbox((0, 0), trial, font=fnt)
        if bbox[2] - bbox[0] > max_width and line:
            draw.text((x, y), line, font=fnt, fill=fill)
            y += (bbox[3] - bbox[1]) + line_gap
            line = ch
        else:
            line = trial
    if line:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        draw.text((x, y), line, font=fnt, fill=fill)
        y += (bbox[3] - bbox[1]) + line_gap
    return y


def draw_slide(
    title: str,
    subtitle: str,
    bullets: list[str],
    index: int,
    total: int,
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 16, HEIGHT), fill=ACCENT)

    brand = font(32)
    title_f = font(64)
    sub_f = font(30)
    bullet_f = font(34)
    foot_f = font(26)

    draw.text((72, 64), "漫序 Studio", font=brand, fill=MUTED)
    draw.text((72, 64 + 48), "产品实操汇报", font=font(24), fill=(100, 100, 98))

    y = 200
    y = draw_wrapped(draw, title, (72, y), WIDTH - 160, title_f, FG, line_gap=12)
    y += 12
    y = draw_wrapped(draw, subtitle, (72, y), WIDTH - 160, sub_f, MUTED, line_gap=10)
    y += 36

    # Content card
    card_top = y
    card_bottom = HEIGHT - 100
    draw.rounded_rectangle(
        (56, card_top, WIDTH - 56, card_bottom),
        radius=18,
        fill=CARD,
        outline=(48, 48, 54),
        width=2,
    )

    by = card_top + 40
    for bullet in bullets:
        draw.ellipse((88, by + 12, 104, by + 28), fill=ACCENT)
        by = draw_wrapped(
            draw,
            bullet,
            (128, by),
            WIDTH - 220,
            bullet_f,
            FG,
            line_gap=14,
        )
        by += 22

    draw.text(
        (72, HEIGHT - 72),
        f"{index} / {total}",
        font=foot_f,
        fill=MUTED,
    )
    return img


def audio_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def burn_subtitles(video: Path, audio: Path, srt: Path, final: Path) -> None:
    """Burn captions via Pillow overlay (this ffmpeg build has no libass/drawtext)."""
    subprocess.check_call(
        [
            "python3",
            str(ROOT / "burn_subs_overlay.py"),
            "--video",
            str(video),
            "--audio",
            str(audio),
            "--srt",
            str(srt),
            "--out",
            str(final),
        ]
    )


def main() -> None:
    chapters = json.loads((ROOT / "chapters.json").read_text(encoding="utf-8"))
    audio = OUT / "narration.mp3"
    srt = OUT / "narration.srt"
    if not audio.exists():
        raise SystemExit("missing narration.mp3 — run generate_voice.py first")

    total_audio = audio_duration(audio)
    planned = sum(float(c["seconds"]) for c in chapters) or 1.0
    scale = total_audio / planned

    slides_dir = OUT / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        concat_lines: list[str] = []
        for i, chapter in enumerate(chapters, start=1):
            img = draw_slide(
                chapter["title"],
                chapter["subtitle"],
                list(chapter.get("bullets") or []),
                i,
                len(chapters),
            )
            png = slides_dir / f"slide_{i:02d}.png"
            img.save(png)
            duration = float(chapter["seconds"]) * scale
            concat_lines.append(f"file '{png.resolve()}'")
            concat_lines.append(f"duration {duration:.3f}")
        last = slides_dir / f"slide_{len(chapters):02d}.png"
        concat_lines.append(f"file '{last.resolve()}'")

        list_file = tmp_path / "slides.txt"
        list_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

        silent = OUT / "slides_silent.mp4"
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-vf",
                "fps=30,format=yuv420p",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(silent),
            ]
        )

    final = OUT / "manxu-studio-report.mp4"
    if srt.exists():
        burn_subtitles(silent, audio, srt, final)
    else:
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(silent),
                "-i",
                str(audio),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(final),
            ]
        )
    print(f"wrote {final} ({total_audio:.1f}s audio)")


if __name__ == "__main__":
    main()
