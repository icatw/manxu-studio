# 0036 — 种气泡默认摆位（竖条 P0）

## Goal

Seed speech bubbles for vertical webtoon reading: top-center band, vertical stack, width-by-length, weak speaker tails. No vision avoidance.

## Done when

- [x] `default_seed_bubble_geometry` + speaker tail helpers
- [x] `seed_lettering_from_dialogue` uses helpers; loads project cast names once
- [x] Unit tests (no panel-index parity)
- [x] PRD seed note +制作预览 helper copy

## Verification

- `pytest tests/test_lettering_seed_geometry.py tests/test_lettering_split_and_shell.py tests/test_lettering_service.py` — 15 passed
