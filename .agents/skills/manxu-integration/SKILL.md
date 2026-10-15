---
name: manxu-integration
description: Coordinate a Manxu Studio change that crosses React and FastAPI, changes the OpenAPI contract, or carries account-owned data through an asynchronous task to the UI. Use for end-to-end feature work and integration debugging.
---

# Manxu Integration Engineering

Own the contract between browser, API, database, queue/worker, provider, and rendered result. Work as the senior engineer responsible for the entire user journey, not only the layer where the symptom appeared.

## Define the vertical slice

- Start from a confirmed user goal and acceptance conditions in `docs/product/prd.md` and `docs/product/user-flows.md`.
- Trace the current path from route entry through query/mutation, API operation, authentication, persistence, task queue, provider, durable result, refresh, and final UI state.
- List the resource owner and stable identifier at every boundary. Confirm that the account/project relationship survives task creation and that every poll, retry, image, and download is scoped to the same owner.
- Write down success, validation failure, unauthorized/foreign resource, duplicate submit, provider failure, timeout, worker restart, stale configuration, and browser refresh behavior before implementing.
- Split work into a vertical slice with one contract and one persisted outcome. Keep the harness plan current and identify which checks prove each acceptance criterion.

## Contract synchronization

- Treat the OpenAPI YAML as the shared request/response source. Update it first, including operation ID, request schema, success status, error envelope, security, task result/error shape, and generated-task polling contract.
- Generate TypeScript types from YAML. Do not hand-edit generated declarations or allow frontend and backend to invent parallel DTOs.
- Check runtime FastAPI routes and actual response bodies against the contract. Route presence and operation-ID equality alone do not establish response schema or error-shape compatibility.
- Keep HTTP status and application error code consistent. Preserve `204`, redirects, and downloads as their documented non-envelope forms.
- Preserve `code`, `message`, `data`, and `request_id` through the shared frontend client; for task errors, use the documented structured error fields rather than reading a stale `detail` property by guesswork.
- Identify the canonical owner of every value crossing layers: OpenAPI for transport shape, backend capability/configuration for supported models and task policy, PostgreSQL for durable account/task state, and query cache for the browser's server-state view. Do not maintain independent handwritten copies when one layer can expose or generate the value.
- When a setting is user- or operator-controlled, define where it is edited, validated, persisted, and consumed. A successful settings save must affect the actual provider/worker path, not only the UI representation.
- Keep translation explicit at boundaries. Avoid repeating status/model/error conversions in multiple screens or handlers; add one mapping at the owning boundary and test unknown/future values deliberately.

## Authenticated browser/API flow

- Verify session bootstrap, CSRF refresh, credentialed requests, and logout using the shared frontend API client. Never reproduce cookie/CSRF logic inside a feature service.
- Verify account ownership in both the route dependency and child-resource traversal. Test that account A cannot observe or mutate account B's resources, and that missing/foreign resources have the same public response.
- On expired sessions, verify the browser returns to sign-in and preserves a safe return path. Do not turn authorization failures into empty data or generic success.

## Async task lifecycle across layers

- Submit a task once and persist its input and ownership before scheduling. A queue outage must have a defined durable recovery path and truthful response to the caller.
- Model `queued -> running -> succeeded|failed|cancelled` (and explicit retry linkage) consistently in OpenAPI, backend state, and frontend UI. Define which transitions are legal and who owns them.
- Ensure idempotency spans HTTP submission, PostgreSQL task creation, Redis job IDs, worker delivery, and provider submission. Verify the queue's result-key retention and duplicate-ID behavior under timeout/restart.
- Persist provider submission IDs before polling. A restart must resume the same remote work when supported; it must not silently create a new billable provider request.
- Bind a remote task ID to the provider, model, endpoint/config revision, and original input fingerprint without persisting credentials. If the user explicitly retries a terminal failure, clear terminal checkpoints and create a fresh provider job; if work is still running, resume the original job instead.
- Save each completed pipeline stage or make its handler idempotent. A whole-pipeline retry must not regenerate already completed text/images or pair a prior image with changed prompt data.
- Keep polling bounded and back off. Stop at terminal state; surface progress, partial warnings, stable failure message/request ID, and a retry action that creates or resumes the correct task.
- Verify that the final asset is stored durably and remains readable after browser refresh; do not rely on provider temporary URLs.

## End-to-end integration proof

- For a feature crossing React and API, test one realistic vertical user path from browser action through API and durable state to refreshed UI.
- Include request serialization/content type, CSRF, response envelope, success/error status, query invalidation, and generated type alignment.
- For asynchronous flows, include worker/Redis behavior, repeated polling, terminal state, failure/retry, and restart recovery. Prefer disposable PostgreSQL/Redis services in CI or Compose smoke tests for infrastructure semantics.
- Use mocked providers to make tests deterministic; separately label any live-provider validation and its cost/credential prerequisites.
- When a full environment is unavailable, report the exact unverified boundary. Passing component tests does not prove the integrated feature works.
- For cross-layer performance changes, record the baseline and verify the complete user path after the change. A faster isolated function is not evidence if queue wait, duplicate work, database load, or UI polling becomes worse.
