#!/usr/bin/env bash
# Concatenate AI-narrated report + live product walkthrough into one MP4.
# Product clip is trimmed/padded to the *spoken* narration length (no trailing silence).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/out"
REPORT="$OUT/manxu-studio-report.mp4"
LIVE="$OUT/product-live.webm"
PRODUCT_VO="$OUT/product-narration.mp3"
PRODUCT_SRT="$OUT/product-narration.srt"
FINAL="$OUT/manxu-studio-demo-final.mp4"

need() { [[ -f "$1" ]] || { echo "missing $1" >&2; exit 1; }; }
need "$REPORT"
need "$LIVE"
need "$PRODUCT_VO"

dur() {
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1"
}

VO_DUR="$(dur "$PRODUCT_VO")"
LIVE_DUR="$(dur "$LIVE")"
# Prefer spoken length: trim long video; if video is shorter, keep video (-shortest later).
CLIP_DUR="$VO_DUR"
awk -v a="$LIVE_DUR" -v b="$VO_DUR" 'BEGIN { if (a < b) exit 1; exit 0 }' || CLIP_DUR="$LIVE_DUR"

SCALED="$OUT/product-live-scaled.mp4"
ffmpeg -y -i "$LIVE" -t "$CLIP_DUR" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p" \
  -an "$SCALED"

LIVE_VO="$OUT/product-live-vo.mp4"
if [[ -f "$PRODUCT_SRT" ]]; then
  python3 "$ROOT/burn_subs_overlay.py" \
    --video "$SCALED" \
    --audio "$PRODUCT_VO" \
    --srt "$PRODUCT_SRT" \
    --out "$LIVE_VO"
else
  ffmpeg -y -i "$SCALED" -i "$PRODUCT_VO" \
    -c:v copy -c:a aac -b:a 192k -shortest "$LIVE_VO"
fi

R_N="$OUT/_report_n.mp4"
L_N="$OUT/_live_n.mp4"
ffmpeg -y -i "$REPORT" -c:v libx264 -c:a aac -ar 48000 -ac 2 -b:a 192k -vf "fps=30,format=yuv420p" "$R_N"
ffmpeg -y -i "$LIVE_VO" -c:v libx264 -c:a aac -ar 48000 -ac 2 -b:a 192k -vf "fps=30,format=yuv420p" "$L_N"

LIST="$OUT/_concat.txt"
printf "file '%s'\nfile '%s'\n" "$R_N" "$L_N" >"$LIST"
ffmpeg -y -f concat -safe 0 -i "$LIST" -c copy "$FINAL"

ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL"
ls -lh "$FINAL"
echo "final=$FINAL"
