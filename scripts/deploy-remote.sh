#!/usr/bin/env bash
set -euo pipefail

# Thin remote deploy helper:
#   ./scripts/deploy-remote.sh user@host [/remote/path/to/repo]
#
# Prerequisites on the VPS: Docker Compose v2.24+, git clone of this repo,
# filled .env.prod, and DNS A/AAAA for DOMAIN pointing at the host.

usage() {
  printf '%s\n' "Usage: $0 user@host [remote_repo_path]" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage
REMOTE="$1"
REMOTE_PATH="${2-}"
if [[ -z "$REMOTE_PATH" ]]; then
  REMOTE_PATH="manxu-studio"
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf '%s\n' "Syncing to ${REMOTE}:${REMOTE_PATH} …"
ssh "$REMOTE" "mkdir -p ${REMOTE_PATH}"
rsync -az --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude 'frontend/test-results' \
  --exclude 'frontend/playwright-report' \
  --exclude 'var' \
  --exclude 'backend/.data' \
  --exclude '.env' \
  --exclude '.env.prod' \
  "$ROOT/" "${REMOTE}:${REMOTE_PATH}/"

if [[ -f "$ROOT/.env.prod" ]]; then
  printf '%s\n' 'Copying local .env.prod to remote (overwrites remote file) …'
  rsync -az "$ROOT/.env.prod" "${REMOTE}:${REMOTE_PATH}/.env.prod"
else
  printf '%s\n' 'No local .env.prod — remote must already have one.'
fi

ssh "$REMOTE" "cd ${REMOTE_PATH} && chmod +x scripts/*.sh && ./scripts/deploy.sh"
