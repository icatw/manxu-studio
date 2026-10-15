.PHONY: dev start stop dev-db stop-db check test test-e2e test-e2e-ai api-types api-lint migrate

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
	uv run --directory backend pytest
	pnpm --dir frontend test

test-e2e:
	docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d api worker frontend
	pnpm --dir frontend test:e2e -- --grep-invert "AI plan"

test-e2e-ai:
	docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d api worker frontend
	pnpm --dir frontend test:e2e:ai

api-types:
	pnpm --dir frontend api:types

api-lint:
	pnpm --dir frontend api:lint

migrate:
	uv run --directory backend alembic upgrade head
