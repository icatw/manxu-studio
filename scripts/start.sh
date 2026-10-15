#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'Docker is required. Install Docker Desktop and retry.' >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  printf '%s\n' 'Docker Compose v2 is required. Update Docker Desktop and retry.' >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf '%s\n' 'Created .env from .env.example. Add OAuth/model secrets before production use.'
fi

docker compose --profile local up -d --build
printf '%s\n' 'Manxu Studio is available at http://localhost:5173'
printf '%s\n' 'API docs: http://localhost:8000/docs'
printf '%s\n' 'Mailpit: http://localhost:8025'
