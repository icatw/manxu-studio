# 0010 Elegant generation architecture

## Goal

Make async generation maintainable: provider adapters, task handler registry, server-side story pipeline, shared ARQ pool.

## Done

- `backend/app/providers/` — OpenAI-compatible text, Qwen image, local object store
- `backend/app/tasks/` — TaskType, registry, handlers, runtime; no if-chain dispatch
- `story_pipeline` + `POST /projects/{project_id}/story-generations` — FE submits once
- Shared ARQ pool with API lifespan close
- Image model allowlist from settings (not OpenAPI Literal)
- FE `domain-mappings.ts`; removed fake image provider factory
- Verified: backend ruff/mypy/46 pytest; frontend vitest 9 + tsc

## Branch / worktree

- Branch: `refactor/elegant-generation-architecture`
- Worktree: `/Users/icatw/code/kaiying-wt-arch-elegance`
