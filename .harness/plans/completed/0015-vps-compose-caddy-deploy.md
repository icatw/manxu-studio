# 0015 VPS Compose + Caddy one-click deploy

## Goal

Ship single-VPS production deploy on top of the existing Compose stack: TLS via Caddy, hardened env, no public DB/Redis/API ports, real SMTP; phase-1 images stay on `image-data`.

## Done

- [x] `docker-compose.prod.yml` + `deploy/Caddyfile`
- [x] Mailpit moved to Compose profile `local`; `start.sh` / e2e updated
- [x] `.env.prod.example` + `scripts/check-prod-env.sh`
- [x] `scripts/deploy.sh` / `deploy-remote.sh` + `make deploy`
- [x] `docs/delivery/deploy-vps.md`, ADR-003, README / harness updates

## Verify

- `./scripts/check-prod-env.sh` rejects empty secrets / Mailpit SMTP / non-https origins
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod config` → services api/worker/frontend/postgres/redis/caddy; no mailpit; no host ports on DB/API
