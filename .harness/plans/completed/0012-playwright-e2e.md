# Playwright E2E for Serial Layer

## Goal

Upgrade local DB to serial-layer head and add Playwright browser E2E covering auth, disposable project lifecycle, serial overview (bible/threads/episodes/reader), plus an opt-in live AI plan + summary path using the existing account model credentials.

## Acceptance

- Alembic at `20261021_serial_layer`.
- Playwright harness under `frontend/e2e` with Mailpit-backed email login.
- Core journey passes against Compose (frontend :5173, API :8000, Mailpit :8025).
- Live AI journey runs when `E2E_LIVE_AI=1` (uses configured account keys; may spend tokens).
- Disposable projects created by tests are deleted; existing user projects are not modified beyond AI path needs.
- Record commands and results; update `.harness/status.md`.

## Progress

- [x] Fix alembic revision ID length (`20261020_char_ref_lock`) and migrate to head.
- [x] Point API SMTP at Mailpit via `docker-compose.e2e.yml` (host `.env` QQ SMTP would otherwise win).
- [x] Add Playwright config, helpers, and specs; mount Sonner `Toaster`; raise nginx `/api` proxy timeouts to 300s.
- [x] Core E2E passed (~2s): login → create → bible/threads → episodes → reader/studio → delete.
- [x] Live AI E2E passed (~54s) with `E2E_LIVE_AI=1`: plan (3 话) → create → summary → read → delete.
- [x] Update status / move plan when done.

## Commands

```bash
SMTP_HOST=mailpit SMTP_PORT=1025 SMTP_STARTTLS=false SMTP_USERNAME= SMTP_PASSWORD= \
  docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d api worker frontend
pnpm --dir frontend test:e2e -- e2e/serial-core.spec.ts
E2E_LIVE_AI=1 pnpm --dir frontend test:e2e -- e2e/serial-ai.spec.ts
# or: make test-e2e / make test-e2e-ai
```

## Notes

- Live AI login uses `e2e-serial@manxu.dev` identity linked to the account that already has text/image keys.
- Core specs use disposable `@manxu.dev` addresses (`.local` is rejected by EmailStr).
