#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env.prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  printf '%s\n' "Missing $ENV_FILE — copy .env.prod.example and fill production values." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# Read KEY=VALUE lines; ignore comments and blanks.
while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    '' | \#*) continue ;;
  esac
  if [[ "$line" == *=* ]]; then
    key="${line%%=*}"
    value="${line#*=}"
    # Trim optional surrounding quotes.
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    printf -v "$key" '%s' "$value"
    export "$key"
  fi
done <"$ENV_FILE"
set +a

fail() {
  printf 'prod-env: %s\n' "$*" >&2
  exit 1
}

require_nonempty() {
  local name="$1"
  local value="${!name-}"
  if [[ -z "${value// }" ]]; then
    fail "$name must be set"
  fi
}

require_nonempty DOMAIN
require_nonempty POSTGRES_PASSWORD
require_nonempty MODEL_ENCRYPTION_KEY
require_nonempty EMAIL_CODE_PEPPER
require_nonempty SMTP_HOST
require_nonempty SMTP_FROM
require_nonempty CORS_ORIGINS
require_nonempty FRONTEND_BASE_URL

if [[ "${APP_ENV:-}" != "production" ]]; then
  fail "APP_ENV must be production (got '${APP_ENV:-}')"
fi

if [[ "${SESSION_COOKIE_SECURE:-}" != "true" ]]; then
  fail "SESSION_COOKIE_SECURE must be true"
fi

if [[ "${ALLOW_PRIVATE_MODEL_BASE_URLS:-false}" == "true" ]]; then
  fail "ALLOW_PRIVATE_MODEL_BASE_URLS must not be true in production"
fi

if [[ "${#MODEL_ENCRYPTION_KEY}" -lt 32 ]]; then
  fail "MODEL_ENCRYPTION_KEY must be at least 32 characters"
fi

if [[ "${#EMAIL_CODE_PEPPER}" -lt 32 ]]; then
  fail "EMAIL_CODE_PEPPER must be at least 32 characters"
fi

host_lc="$(printf '%s' "$SMTP_HOST" | tr '[:upper:]' '[:lower:]')"
case "$host_lc" in
  mailpit | localhost | 127.0.0.1 | ::1)
    fail "SMTP_HOST must be a real mail server (not Mailpit/localhost)"
    ;;
esac

if [[ "$CORS_ORIGINS" != https://* ]]; then
  fail "CORS_ORIGINS must use https://"
fi

if [[ "$FRONTEND_BASE_URL" != https://* ]]; then
  fail "FRONTEND_BASE_URL must use https://"
fi

expected_origin="https://${DOMAIN}"
if [[ "$FRONTEND_BASE_URL" != "$expected_origin" && "$FRONTEND_BASE_URL" != "$expected_origin/" ]]; then
  fail "FRONTEND_BASE_URL must match https://\$DOMAIN (expected $expected_origin)"
fi

printf '%s\n' "prod-env: $ENV_FILE OK"
