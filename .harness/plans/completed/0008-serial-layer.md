# Serial layer (Phase 2)

## Goal

Unfreeze and implement 连载: season plan, plot threads, episode summary/continuity, project bible, overview tabs, reading page.

## Tasks

- [x] PRD / flows / screens / glossary unfreeze (SERIAL-*, PROJ-04)
- [x] Project bible fields + episode summary + plot_threads + OpenAPI
- [x] Continuity injection into storyboard generation
- [x] Plan API + create-from-plan + frontend new/overview/reader routes
- [x] Tests (continuity, regression) and status update

## Domain

Project = 作品; Episode = 话. Keep API resource names.

## Verification

- Backend pytest: 56 passed (incl. continuity)
- Frontend: typecheck + Vitest
- OpenAPI: redocly lint passed
