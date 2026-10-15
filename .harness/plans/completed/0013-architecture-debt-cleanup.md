# Architecture Debt Cleanup

## Goal

Pay down layering, config, contract honesty, and frontend dual-model debt in branch `arch/debt-cleanup` (worktree `../kaiying-arch-debt`).

## Decisions

- Remove `cancelled` from contract (no cancel API).
- Extract application services for projects/assets/storyboard/generations/model_config/auth.
- Unify generation SLA in Settings; delete dead env model credential fields.
- Frontend: Query-owned task polling; catalogs; split StudioProvider; `useCurrentAccount`.

## Work

- [x] Contract: drop cancelled
- [x] Settings SLA + dead fields + default image model
- [x] Backend services + thin routes
- [x] Kill façades
- [x] Frontend Query poll + mapping + provider split
- [x] Docs + verification

## Verification

- Backend: `uv run ruff check app tests` pass; `uv run pytest -q` → **93 passed**
- Frontend: `npm run typecheck` pass; `npm test` → **9 passed** (3 files); Vitest excludes `e2e/`
- Docs: `docs/technical/architecture.md` updated for services layer, catalogs, Query polling, no `cancelled`, Settings SLA
- Fixes during verify: auth path `/auth/github/start`; logout CSRF only for valid sessions; test imports→services; qwen poll settings in fixtures; retry_policy patches `generations_service`
