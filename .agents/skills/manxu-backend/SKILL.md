---
name: manxu-backend
description: Build or change Manxu Studio FastAPI routes, SQLAlchemy persistence, authentication, provider adapters, Redis queues, ARQ workers, or exports. Use for backend implementation and API/runtime defects.
---

# Manxu Backend Engineering

Work as a senior Python backend engineer in the existing Python 3.13, FastAPI, Pydantic v2, SQLAlchemy async, PostgreSQL, Redis, and ARQ application. Preserve the documented boundaries and prove behavior at the boundary where it matters.

## Contract and ownership

- For an HTTP behavior change, update the confirmed PRD requirement and `docs/api/openapi.yaml` before implementing the route or frontend type changes. Keep status codes, envelope, errors, authentication, and examples accurate.
- Keep route handlers thin: parse HTTP input, resolve dependencies, call an owning service, and return the documented response. Put business rules in the service/domain layer and wire them through explicit dependencies.
- Use the shared `current_account` and resource-owner dependencies. Every project child resource must be authorized through its project and current account; absent and foreign-owned resources must follow the documented non-disclosure response.
- Do not infer ownership from request path strings, client-submitted account IDs, task payloads, or a global account registry.
- Keep SQLAlchemy models, Pydantic schemas, migrations, OpenAPI, and response views consistent. A migration must be reversible when feasible and tested against both existing and new rows.

## Persistence and transactions

- Treat PostgreSQL as the durable source for accounts, resource ownership, task state, provider checkpoints, and completed results. Redis is a queue/cache/limiter, not the only record that work exists.
- Make transaction boundaries explicit. Commit state needed by another process before enqueueing or external calls; do not hold an open transaction or connection while waiting on a provider or SMTP server.
- When mutating JSON columns in place, ensure SQLAlchemy tracks the mutation and verify the committed value after a fresh read. Do not swallow persistence errors to accommodate test doubles.
- Handle uniqueness conflicts and concurrent updates at the database boundary. Application-level “check then insert” is not a substitute for a database constraint when duplicate creation is possible.
- Use one async session per request/job scope. Do not share sessions or ORM instances across concurrent coroutines.

## Module boundaries and policy

- Organize backend code by business capability and lifecycle, with clear boundaries between HTTP transport, application orchestration, domain rules, persistence, and external adapters. A route should not become the place where provider policy, ownership rules, and transaction choreography accumulate.
- Split a service/module when it has independent reasons to change, separate transaction or retry semantics, or external dependencies that need isolation. Keep cohesive orchestration together when extraction would create circular calls or hide the transaction boundary.
- Avoid both oversized “manager/service” modules and generic repository/util layers that only rename one SQL call or pass data through. Introduce an interface when there is a real substitution, protocol boundary, or isolation need.
- Keep conditionals that encode a small, explicit domain rule readable. Use exhaustive enum/state dispatch for a closed set of states; use a typed registry/strategy when implementations are independently extensible or have distinct protocols/lifecycles. Do not use stringly typed dispatch or a registry just to remove visible `if` statements.
- Put operator-controlled values in validated settings and account/project-controlled values in persisted configuration. Give configuration one owner, explicit precedence, safe defaults, and validation at startup or update time. Keep protocol constants and security invariants named and fixed rather than exposing them as arbitrary settings.
- Do not duplicate supported provider/model lists, task transition policy, retry limits, or concurrency semantics in routes, workers, and UI-facing responses. Expose server-owned capabilities through the API or derive them from a canonical registry/configuration.
- Before performance work, capture an observable baseline such as query count/latency, queue wait, provider time, memory, or throughput. Optimize the measured path and test its consistency/recovery costs; do not add speculative caching, parallelism, or batching.

## Authentication, security, and errors

- Browser mutations use HttpOnly session cookies plus the shared CSRF dependency; Bearer support must follow the documented API-client boundary.
- Validate public HTTPS URLs before outbound requests and disable redirects where they could bypass validation. Bound request time, response size, and accepted content types.
- Encrypt provider credentials at rest. Return configured/clear status only; never serialize secret material or include it in logs, exception messages, URLs, or task result payloads.
- Return the project JSON envelope and stable error code. Unexpected failures return a generic message and request ID; retain diagnostic traceback only in sanitized server logs.
- Map provider errors into stable application-level categories. Do not leak raw provider bodies, tokens, filesystem paths, SQL, or stack traces to clients.

## Providers and asynchronous tasks

- Keep provider protocol, payload normalization, polling, download validation, and object storage behind provider interfaces. Keep task handlers focused on orchestration and persistence, not HTTP wire details.
- Register task handlers through the typed registry. Validate at startup or in tests that every supported task type has one handler and duplicate registrations fail clearly.
- Persist task state and enough input/configuration metadata to resume deterministically. Persist remote provider task IDs immediately after submission; do not assume a local timeout cancels remote work.
- Persist a non-secret provider/model/base-URL or configuration-version snapshot for resumable work. Resolve credentials through the account's current secret store, and fail with an actionable configuration-changed error rather than polling an old provider task against an unrelated endpoint. Never copy provider checkpoints into a fresh explicit retry unless the provider job is known to still be resumable.
- Define legal task transitions and make progress monotonic. Terminal states must stay terminal unless an explicit retry creates a linked new task.
- Design for duplicate delivery, worker process death at every await/commit boundary, Redis unavailability, timeout, provider failure, and concurrent duplicate submissions. Use database constraints/advisory locks or idempotency keys where the invariant requires them.
- Verify queue-library semantics, including job-ID uniqueness, result retention, retry count, timeout behavior, and when a scheduled requeue can actually enqueue. Do not infer recovery from a periodic database scan alone.
- Never hold a database transaction across provider polling. Reopen/refresh durable state at clear checkpoints and ensure a resumed handler does not repeat completed costly stages or attach stale outputs to changed inputs.

## Verification

- Add tests for success and failure semantics at the service/API boundary. Cover ownership denial, validation, concurrency/duplicate delivery, transaction checkpoints, recovery, and sanitized error output where affected.
- Stub external HTTP with deterministic transports/fakes; do not spend live model quota in ordinary CI. Reserve live-provider smoke tests for an explicitly configured, opt-in environment.
- Run `uv run --directory backend ruff check .`, `ruff format --check .`, `mypy app`, and `pytest`. For API changes, run the OpenAPI linter/type generation and inspect the generated-type diff.
- For queue/provider changes, verify the actual queue and worker behavior with a Redis-backed integration test or Compose smoke test. Mock-only tests do not prove restart recovery or job-ID semantics.
- Record exact commands and evidence in the active plan. Call out database, Redis, Docker, or provider checks that were unavailable.
