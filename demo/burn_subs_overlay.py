#!/usr/bin/env python3
"""
Burn SRT captions into a video using Pillow + ffmpeg overlay.
Works without libass/drawtext (this Homebrew ffmpeg build lacks both).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
BAR_H = 168
BG = (12, 12, 16, 230)
FG = (245, 245, 240, 255)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size, index=0)
        except OSError:
            continue
    return ImageFont.load_default()


def parse_srt(text: str) -> list[tuple[float, float, str]]:
    def to_sec(ts: str) -> float:
        h, m, rest = ts.split(":")
        s, ms = rest.replace(",", ".").split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0

    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_s, end_s = [p.strip() for p in lines[1].split("-->")]
        body = "\n".join(lines[2:]).strip()
        cues.append((to_sec(start_s), to_sec(end_s), body))
    return cues


def render_bar(text: str) -> Image.Image:
    img = Image.new("RGBA", (WIDTH, BAR_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((48, 8, WIDTH - 48, BAR_H - 8), radius=16, fill=BG)
    fnt = font(34)
    # Center multiline text
    lines = text.split("\n")
    line_heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    total_h = sum(line_heights) + 8 * (len(lines) - 1)
    y = (BAR_H - total_h) // 2
    for line, w, h in zip(lines, widths, line_heights):
        x = (WIDTH - w) // 2
        draw.text((x, y), line, font=fnt, fill=FG)
        y += h + 8
    return img


def audio_or_video_duration(path: Path) -> float:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--srt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    cues = parse_srt(args.srt.read_text(encoding="utf-8"))
    duration = audio_or_video_duration(args.audio)
    empty = Image.new("RGBA", (WIDTH, BAR_H), (0, 0, 0, 0))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        frames_dir = tmp_path / "bars"
        frames_dir.mkdir()
        concat: list[str] = []
        cursor = 0.0
        idx = 0

        def emit(img: Image.Image, start: float, end: float) -> None:
            nonlocal idx
            if end <= start:
                return
            png = frames_dir / f"bar_{idx:04d}.png"
            img.save(png)
            concat.append(f"file '{png.resolve()}'")
            concat.append(f"duration {end - start:.3f}")
            idx += 1

        for start, end, body in cues:
            start = max(0.0, start)
            end = min(duration, end)
            if start > cursor:
                emit(empty, cursor, start)
            emit(render_bar(body), start, end)
            cursor = end
        if cursor < duration:
            emit(empty, cursor, duration)
        # concat demuxer requires repeating last file
        if concat:
            last_file = concat[-2].split("'", 2)[1]
            concat.append(f"file '{last_file}'")

        list_file = tmp_path / "bars.txt"
        list_file.write_text("\n".join(concat) + "\n", encoding="utf-8")
        bars_vid = tmp_path / "bars.mov"
        # qtrle/png keeps alpha for overlay
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
                "-fps_mode",
                "cfr",
                "-r",
                "30",
                "-c:v",
                "qtrle",
                "-pix_fmt",
                "argb",
                str(bars_vid),
            ]
        )

        # Overlay bar near bottom, then mux audio
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(args.video),
                "-i",
                str(bars_vid),
                "-i",
                str(args.audio),
                "-filter_complex",
                f"[0:v][1:v]overlay=0:H-h-36:format=auto,format=yuv420p[v]",
                "-map",
                "[v]",
                "-map",
                "2:a",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(args.out),
            ]
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
