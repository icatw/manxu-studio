# 0037 — 字效一键布局模板（LETTER-08）

## Goal

In 制作预览, let authors re-layout existing lettering on the **current panel** with rule templates: top band, L/R dialogue, bottom bar. Positions only; no vision.

## Done when

- [x] PRD LETTER-08 confirmed
- [x] Pure template helper + unit tests
- [x] Preview UI: three actions when current panel has lettering
- [x] Sequential PATCH via existing lettering API

## Notes

- Client-only geometry; copy clarifies rearrange ≠ face avoidance.
- Deferred: vision avoidance, drag-width, rotate.
