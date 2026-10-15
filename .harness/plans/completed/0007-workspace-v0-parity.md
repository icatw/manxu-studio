# Workspace v0 parity (Phase 1)

## Goal

Close confirmed-scope gaps with the v0 prototype: production JSON export, panel composition/story purpose editing, multi-episode shell, character reference lock, and project library thumbnails.

## Tasks

- [x] Export toolbar: PNG + production_json
- [x] Panel inspector: composition + story_purpose
- [x] Episode list / switch / create in workspace
- [x] reference_locked (PRD + OpenAPI + DB + UI + regen/image refs)
- [x] Project.cover_image_url + card library UI
- [x] Tests (character lock, cover URL, production_json); frontend lint/typecheck

## Out of scope (Phase 2)

Season planning, plot threads, chapter summaries, reading page, project style_rules/seed.

## Verification

- Backend: `pytest tests/test_character_reference_lock.py tests/test_project_cover.py` — 4 passed
- Frontend: lint (warnings only), typecheck passed
