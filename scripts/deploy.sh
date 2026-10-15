#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'Docker is required. Install Docker Engine or Docker Desktop and retry.' >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  printf '%s\n' 'Docker Compose v2.24+ is required (supports !reset / !override).' >&2
  exit 1
fi

ENV_FILE="${ENV_FILE:-$ROOT/.env.prod}"
"$ROOT/scripts/check-prod-env.sh" "$ENV_FILE"

# shellcheck disable=SC1090
DOMAIN=""
while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    '' | \#*) continue ;;
  esac
  if [[ "$line" == DOMAIN=* ]]; then
    DOMAIN="${line#DOMAIN=}"
    DOMAIN="${DOMAIN%\"}"
    DOMAIN="${DOMAIN#\"}"
    break
  fi
done <"$ENV_FILE"

if [[ -z "$DOMAIN" ]]; then
  printf '%s\n' 'DOMAIN missing after env check' >&2
  exit 1
fi

printf '%s\n' "Deploying Manxu Studio for https://${DOMAIN} …"
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  --env-file "$ENV_FILE" \
  up -d --build --wait

printf '%s\n' "Manxu Studio: https://${DOMAIN}"
printf '%s\n' "Health:      https://${DOMAIN}/api/v1/health"
printf '%s\n' 'Note: worker has no separate healthcheck; confirm with: docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod ps'
