---
name: manxu-testing
description: Design, run, or review tests for Manxu Studio frontend, FastAPI APIs, database ownership, model integrations, Redis/ARQ workers, or end-to-end workflows. Use when test coverage or verification evidence is part of the task.
---

# Manxu Test Engineering

Act as a senior test engineer. Tests must establish user-visible behavior and system invariants, not merely repeat implementation details or prove that a function was called.

## Choose evidence by risk

- Unit tests prove pure transformations and local state transitions.
- API/service tests prove validation, authorization, response envelopes, persistence behavior, and stable errors at a boundary.
- Infrastructure integration tests prove interactions with PostgreSQL, Redis/ARQ, file/object storage, and transaction/restart behavior.
- Browser tests prove navigation, accessible interaction, async rendering, session handling, and the complete user journey.
- Live-provider tests prove external credentials/availability only; keep them opt-in, isolated, clearly labeled, and never required for ordinary CI unless the repository explicitly configures a safe test account.
- State which evidence class each acceptance check needs. Do not use a passing lower-level test as a substitute for a higher-risk boundary.

## Test behavior, not source shape

- Assert inputs, durable outputs, visible state, and failure/recovery behavior. Avoid tests that assert private helper names, exact call counts without a contract reason, source text, import graphs, or AST structure as a proxy for architecture.
- Prefer testing a policy through the public service/API boundary. Use pure-function tests when the behavior is genuinely pure.
- Do not mock the unit under test. Stub external systems at their protocol boundary and assert the request/response contract and resulting domain state.
- Keep tests deterministic: freeze time where relevant, use stable IDs, control polling/backoff, isolate filesystem/database/Redis namespaces, and remove dependence on test order.
- Never print or snapshot API keys, cookies, email codes, OAuth parameters, or production data. Include enough sanitized request/task IDs to diagnose failures.
- Test architecture through observable boundaries: prove that configuration changes affect the real consumer, account ownership holds across child resources, task transitions remain legal under retries, and provider failures recover as documented. Do not assert file names, line counts, class layouts, or a preferred number of conditionals.
- For a refactor, preserve or add characterization tests for the externally visible behavior before moving responsibilities. Compare outcomes and failure semantics after the change; do not treat a cleaner module tree as proof of correctness.
- For performance claims, capture a repeatable baseline and compare the same workload and environment. Include the cost moved elsewhere (for example, fewer requests but larger payloads, more concurrency but higher provider failures, or cache hits but stale data).
- Add a test for a hardcoded-value defect at the behavior boundary: changing the canonical setting/metadata should change the consumer behavior without editing a second copy. Keep true protocol/security invariants fixed and test their rejection behavior.

## Backend coverage

- For API changes, test valid and invalid input, every documented status, response envelope fields, stable error code, request ID, and security dependencies.
- For ownership, test owner success and cross-account denial for both parent and child resources; verify the public not-found behavior does not reveal existence.
- For SQLAlchemy changes, test transaction commit/rollback, fresh-session reads, uniqueness races, JSON mutation tracking, and migration behavior when relevant.
- For provider adapters, use mock HTTP transport to test URL/path construction, auth headers without logging secrets, timeout, non-2xx responses, malformed payloads, output validation, download size/type, and SSRF rejection.
- For task handlers, test legal state transitions, monotonic progress, warnings vs terminal failure, retry linkage, duplicate delivery, idempotent outputs, and cleanup.
- For Redis/ARQ recovery, test real queue semantics: enqueue deduplication while a job is queued, running, completed, failed, or timed out; result retention; requeue after worker interruption; and resume from a persisted remote provider task ID. A fake `enqueue_job` that always accepts does not prove recovery.
- Test the distinction between recovery and user retry: recovery resumes an in-flight remote task, while retrying a terminal provider failure submits a new remote task and does not reuse the failed checkpoint.
- For multi-stage tasks, inject interruption after each durable checkpoint and prove completed stages are not repeated or paired with changed inputs.

## Frontend coverage

- Test accessible user actions and rendered outcomes rather than hook internals. Cover loading, empty, partial success, failure, retry, and stale-session states.
- For API clients/services, test JSON content type, CSRF injection/refresh, envelope unwrapping, stable error preservation, and special handling for `204`, redirects, and file downloads.
- For long-running jobs, test polling interval/backoff, stop conditions, rate-limit behavior, progress monotonicity, unmount/abort behavior, duplicate submit prevention, and refresh behavior.
- For editor/autosave workflows, cover debounce, overlapping edits, out-of-order responses, save failure, undo/redo boundaries, and navigation with unsaved changes where relevant.
- Use Playwright for workflows that combine routes, forms, auth, API calls, task polling, and downloads. Assert the primary action and resulting durable view, not just page load.

## CI and local verification

- The hard gate is the real repository CI: OpenAPI lint/type generation drift check, frontend lint/typecheck/Vitest/build, and backend Ruff/format/mypy/pytest. Keep a regression test in the suite that runs in CI for every fixed defect.
- Run the narrowest relevant tests first, then the appropriate full checks. Use `make check` and `make test` for a full local pass when dependencies are available.
- For UI workflows, run the Playwright path in the same app configuration users use; capture screenshots or traces when they help diagnose layout or race failures.
- For Docker-dependent behavior, use disposable services and wait on readiness/health checks. Do not mutate a shared developer database to make tests pass.
- Report exact commands, counts, and failures. Separate CI evidence from local runs, mocked provider tests from live-provider tests, and API process checks from worker recovery checks.
