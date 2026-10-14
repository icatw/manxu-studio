# Multi-account Authentication and Redis

## Goal

Replace the single-account GitHub pilot with email-code registration, GitHub OAuth login, per-account project isolation, and Redis-backed limits and generation dispatch.

## Accepted Decisions

- Browser requests keep HttpOnly session cookies and CSRF protection; opaque Bearer session tokens remain supported by the backend.
- PostgreSQL remains the durable source for accounts, identities, sessions, tasks, task results, and ownership.
- Redis stores short-lived verification codes and rate-limit counters, and dispatches ARQ jobs.
- Unowned pilot projects are backfilled from `account_registry`; business routes no longer read or write that registry.
- Cross-account resources resolve as `404`.

## Progress

- [x] Confirm account and infrastructure requirements in the PRD and OpenAPI contract.
- [x] Add identity, challenge, nullable GitHub account fields, OAuth intent, and task owner migration.
- [x] Implement email-code account creation/login, GitHub identity login, identity listing/removal, Cookie and Bearer session lookup.
- [x] Add project ownership checks to all workspace routes and cross-account API regression coverage.
- [x] Add Redis rate limits, expiring code storage, ARQ dispatch, worker recovery scan, and duplicate task lock.
- [x] Add login resend countdown and email edit controls; show identity status in account settings.
- [x] Add Redis, Mailpit, API, worker, and persistent image volumes to Docker Compose.
- [x] Finish email account flow and start Compose worker runtime; GitHub flow remains credential-gated.
- [x] Run frontend lint, typecheck, Vitest, production build, backend pytest/ruff/mypy, and OpenAPI checks.
- [x] Update status with final verification and remaining runtime prerequisites.

## Verification Notes

- Before applying the migration, the local database had zero projects and generation tasks with a null owner; the existing registry pointed to the original account.
- Alembic is at `20261016_multi_account_auth` locally.
- Email delivery requires Redis. Development uses Mailpit in Compose or a generated process-local pepper plus console delivery when SMTP is not configured. Production must configure `EMAIL_CODE_PEPPER` and SMTP.
- GitHub OAuth requires deployment credentials and the registered callback URL.
- Compose health check passed for PostgreSQL, Redis, Mailpit, and API; the ARQ worker is running without a health endpoint.
- Mailpit end-to-end test requested a code, read it from the local inbox, verified it, and reused the session for `/auth/me`.

## Known Boundaries

- Team and organization permissions are out of scope.
- Explicitly linking a new provider identity to an already signed-in account remains deferred; provider identities can log in to their own account.
- Access tokens for non-browser API clients are not separately issued; Bearer accepts an existing opaque account session token.
