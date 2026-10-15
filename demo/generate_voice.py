#!/usr/bin/env python3
"""Generate Chinese TTS via Microsoft Edge online neural voices (edge-tts).

This calls a cloud TTS endpoint (same family as Edge Read Aloud). It is not a
local model and not OpenAI/DashScope; it needs network access.
Also writes an SRT subtitle file from WordBoundary events when possible.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
DEFAULT_TEXT = ROOT / "narration.txt"
DEFAULT_OUT = ROOT / "out" / "narration.mp3"
DEFAULT_SRT = ROOT / "out" / "narration.srt"
# Neural Mandarin; alternatives: zh-CN-XiaoxiaoNeural, zh-CN-YunyangNeural
DEFAULT_VOICE = "zh-CN-YunxiNeural"


def _wrap_srt_lines(text: str, max_chars: int = 22) -> str:
    """Break long Chinese lines for readable burned-in subtitles."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    lines: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if len(buf) >= max_chars and ch in "，。；、：！？,.!?; ":
            lines.append(buf.strip())
            buf = ""
        elif len(buf) >= max_chars + 6:
            lines.append(buf.strip())
            buf = ""
    if buf.strip():
        lines.append(buf.strip())
    # Max 2 lines per cue for readability
    if len(lines) <= 2:
        return "\n".join(lines)
    return "\n".join(lines[:2])


async def synthesize(text: str, voice: str, out: Path, srt_out: Path, rate: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    submaker = edge_tts.SubMaker()
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            submaker.feed(chunk)
    out.write_bytes(audio)

    raw_srt = submaker.get_srt()
    if not raw_srt.strip():
        # Fallback: one cue for whole file
        srt_out.write_text(
            "1\n00:00:00,000 --> 00:10:00,000\n" + _wrap_srt_lines(text[:80]) + "\n",
            encoding="utf-8",
        )
    else:
        # Re-wrap cue text for CJK readability
        blocks = raw_srt.strip().split("\n\n")
        rewritten: list[str] = []
        for block in blocks:
            lines = block.splitlines()
            if len(lines) < 3:
                rewritten.append(block)
                continue
            idx, timing, *payload = lines
            body = _wrap_srt_lines("".join(payload))
            rewritten.append(f"{idx}\n{timing}\n{body}")
        srt_out.write_text("\n\n".join(rewritten) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", type=Path, default=DEFAULT_TEXT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--srt", type=Path, default=None)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", default="+0%", help="edge-tts rate")
    args = parser.parse_args()
    text = args.text.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"empty narration: {args.text}")
    srt_out = args.srt or args.out.with_suffix(".srt")
    asyncio.run(synthesize(text, args.voice, args.out, srt_out, args.rate))
    print(f"wrote {args.out}")
    print(f"wrote {srt_out}")


if __name__ == "__main__":
    main()
