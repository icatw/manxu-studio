# Workspace Route Module Split

## Goal

Split the monolithic FastAPI workspace router into resource-focused modules without changing public API behavior.

## Decisions

- Keep paths, operation IDs, response models, status codes, CSRF, rate limits, and ownership dependencies unchanged.
- Keep shared account setup, route dependencies, serialization helpers, and task creation in `workspace_common.py`.
- Register the resource routers through `app.api.router`; retain a compatibility aggregation module only if repository callers still require it.
- Update isolation tests to override the actual `current_account` dependency instead of monkeypatching a symbol in the route module.

## Progress

- [x] Inspect route ownership checks, API tests, OpenAPI contract checks, and harness rules.
- [x] Extract project and episode routes.
- [x] Extract character and scene routes.
- [x] Extract storyboard and image-version routes.
- [x] Extract generation, export, and asset routes.
- [x] Register routers and update direct-import tests.
- [x] Run Ruff, mypy, pytest, and verify runtime OpenAPI operation IDs remain unchanged.
- [x] Update status and archive this plan.

## Result

- `workspace.py` is now a small compatibility aggregator; runtime registration uses four resource routers directly.
- Shared session/account setup, router dependencies, task enqueueing, and serialization helpers live in `workspace_common.py`.
- Isolation tests now override `current_account_dependency` directly.
- Ruff and mypy pass; all 27 backend tests pass.
- Compared to the previous Git revision, all 28 workspace route method/path/operationId triples are unchanged.
