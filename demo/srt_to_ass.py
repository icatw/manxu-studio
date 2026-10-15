#!/usr/bin/env python3
"""Convert SRT to ASS with a readable Chinese subtitle style."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,PingFang SC,36,&H00F5F5F0,&H000000FF,&H64000000,&H64000000,0,0,0,0,100,100,0,0,3,2,0,2,60,60,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def srt_time_to_ass(ts: str) -> str:
    # 00:00:02,175 -> 0:00:02.17
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return f"{int(h)}:{m}:{s}.{ms[:2]}"


def convert(srt_text: str) -> str:
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    lines = [HEADER]
    for block in blocks:
        parts = block.strip().splitlines()
        if len(parts) < 3:
            continue
        timing = parts[1]
        if "-->" not in timing:
            continue
        start, end = [p.strip() for p in timing.split("-->")]
        text = "\\N".join(parts[2:]).replace("{", "(").replace("}", ")")
        lines.append(
            f"Dialogue: 0,{srt_time_to_ass(start)},{srt_time_to_ass(end)},Default,,0,0,0,,{text}\n"
        )
    return "".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("srt", type=Path)
    parser.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or args.srt.with_suffix(".ass")
    out.write_text(convert(args.srt.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
