# Playground API + Playwright (P0/P1)

## Goal

Ship an isolated Docker playground (separate DB/volumes/ports), real-HTTP API workflow tests with a fake LLM, and hang existing Playwright `serial-core` on the same stack.

## Progress

- [x] `docker-compose.playground.yml` + fake-llm
- [x] Makefile playground targets
- [x] `backend/tests/playground` suite
- [x] Playwright env wiring (frontend host port `15174` to avoid local Vite collisions)
- [x] CI playground job
- [x] Local `make test-api-playground` + Playwright serial-core green
- [x] `ALLOW_PRIVATE_MODEL_BASE_URLS` for `http://fake-llm` in playground only

## Commands

```bash
make playground-up
make test-api-playground
make test-e2e-playground
make test-playground
make playground-down
```

## Verification (2026-10-15)

- API playground: 4 passed (`auth`, serial CRUD, isolation, fake-llm plan/summary)
- Playwright: `e2e/serial-core.spec.ts` 1 passed against `http://127.0.0.1:15174`
