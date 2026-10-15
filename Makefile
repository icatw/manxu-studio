.PHONY: dev start stop dev-db stop-db check test test-e2e test-e2e-ai api-types api-lint migrate \
	playground-up playground-down playground-logs test-api-playground test-e2e-playground test-playground

PLAYGROUND_COMPOSE := docker compose -p manxu-playground -f docker-compose.playground.yml
PLAYGROUND_API_URL := http://127.0.0.1:8001
PLAYGROUND_FRONTEND_URL := http://127.0.0.1:15174
PLAYGROUND_MAILPIT_URL := http://127.0.0.1:8026

dev:
	@echo "Run 'pnpm --dir frontend dev' and 'uv run --directory backend fastapi dev app/main.py' in separate terminals."

start:
	./scripts/start.sh

stop:
	./scripts/stop.sh

dev-db:
	docker compose up -d postgres

stop-db:
	docker compose stop postgres

check: api-lint api-types
	pnpm --dir frontend lint
	pnpm --dir frontend typecheck
	uv run --directory backend ruff check .
	uv run --directory backend ruff format --check .
	uv run --directory backend mypy app

test:
	uv run --directory backend pytest -m "not playground"
	pnpm --dir frontend test

test-e2e:
	docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d api worker frontend
	pnpm --dir frontend test:e2e -- --grep-invert "AI plan"

test-e2e-ai:
	docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d api worker frontend
	pnpm --dir frontend test:e2e:ai

playground-up:
	$(PLAYGROUND_COMPOSE) up -d --build --wait

playground-down:
	$(PLAYGROUND_COMPOSE) down

playground-logs:
	$(PLAYGROUND_COMPOSE) logs --tail=200 api worker fake-llm

test-api-playground: playground-up
	PLAYGROUND_BASE_URL=$(PLAYGROUND_API_URL) \
	PLAYGROUND_MAILPIT_URL=$(PLAYGROUND_MAILPIT_URL) \
	PLAYGROUND_FAKE_LLM_URL=http://fake-llm:8080/v1 \
	uv run --directory backend pytest -m playground -q

test-e2e-playground: playground-up
	E2E_BASE_URL=$(PLAYGROUND_FRONTEND_URL) \
	E2E_MAILPIT_URL=$(PLAYGROUND_MAILPIT_URL) \
	pnpm --dir frontend exec playwright test e2e/serial-core.spec.ts e2e/generation-resume.spec.ts

test-playground: test-api-playground test-e2e-playground

api-types:
	pnpm --dir frontend api:types

api-lint:
	pnpm --dir frontend api:lint

migrate:
	uv run --directory backend alembic upgrade head
