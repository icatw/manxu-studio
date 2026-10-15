# Generation Ownership Close

## Goal

Close the cross-layer generation-task ownership gap: server owns durable status; browser displays, merges safely on hydrate, and resumes active panel tasks after reload. Abort only stops local polling.

## Invariants

- Idempotent submit with the same key reuses `queued` / `running` / `succeeded`; `failed` releases the key so a new task can be created.
- Workspace invalidate/hydrate must not wipe unsaved editor content or in-flight panel runtime.
- Local AbortController is “stop tracking”, not remote cancel (no cancel API yet).
- Entering the studio resumes `queued`/`running` `panel_image*` tasks for the current episode.

## Work

- [x] OpenAPI: expose `project_id` / `episode_id` / `panel_id` on `GenerationTask`; add `listEpisodeGenerationTasks`.
- [x] Backend: idempotency gate; list route; schema sync; tests (`app.services.generations`).
- [x] Frontend: hydrate merge; stop-tracking copy; `complete`/resume; types already on main; tests.
- [x] Rebased onto post–debt-cleanup / playground `main` (Studio persist hook + Query polling).

## Verification

- Backend: `pytest tests/test_task_idempotency.py` (plus suite as available).
- Frontend: `vitest run src/lib/project-store.test.ts`; typecheck/lint on touched modules.
- Playwright: `e2e/generation-resume.spec.ts` (list active tasks → poll → complete after reload); wired into playground CI.
- Not verified: live provider path; remote cancel API (still absent by design).

## Residual

- No server-side cancel endpoint; UI correctly says「停止跟踪」.
- Broader storage port remain architecture follow-ups, not this slice.
