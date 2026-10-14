.PHONY: dev dev-db stop-db check test api-types api-lint migrate

dev:
	@echo "Run 'pnpm --dir frontend dev' and 'uv run --directory backend fastapi dev app/main.py' in separate terminals."

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

api-types:
	pnpm --dir frontend api:types

api-lint:
	pnpm --dir frontend api:lint

migrate:
	uv run --directory backend alembic upgrade head
