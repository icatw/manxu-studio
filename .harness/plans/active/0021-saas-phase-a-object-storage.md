# 0021 SaaS Phase A — object storage (COS)

## Goal

Replace Docker `image-data` volume dependency for production assets with Tencent COS via an S3-compatible `ObjectStore`, per ADR-004. Keep local/CI on `LocalObjectStore`.

## Gate

- [x] Confirm **INFRA-02** in `docs/product/prd.md` (`proposed` → `confirmed`).
- [x] OpenAPI `getImageAsset` documents ownership-checked API proxy (INFRA-02); response shape unchanged (binary stream).

## Decisions

- Provider: Tencent COS; client: S3-compatible (configurable endpoint). ADR-004 `accepted` 2026-10-16.
- Bucket private; default read path = API proxy after ownership check (no public CDN).
- Dependency: `boto3` for S3 API (reason: standard S3-compatible client; async via `asyncio.to_thread`).

## Work

- [x] ADR-004 + architecture / PRD cross-links.
- [x] Confirm INFRA-02; YAML note on `getImageAsset`.
- [x] Settings + `.env*.example` + compose env for `OBJECT_STORE_BACKEND` / `S3_*`.
- [x] `S3ObjectStore` implementing `ObjectStore`; wire Qwen download + export + asset GET.
- [ ] Persist export blobs in object store (still `exports.content` bytea this slice).
- [x] Ownership-checked download: existing API proxy stream (presigned GET deferred).
- [x] One-shot migrate CLI: `python -m app.cli.migrate_images_to_s3` (+ dry-run / verify / skip-existing).
- [x] Tests: mock S3; settings validation; migrate unit tests; local backend still green in CI.
- [x] Cutover + rollback runbook: `docs/delivery/object-storage-cos-cutover.md`.
- [x] Prod: bucket `manxu-assets-1255546834`; migrate **89/89 verified**; `OBJECT_STORE_BACKEND=s3`; `open_asset` smoke OK (2026-10-16). Note: api/worker image was docker-commit hotpatch (boto3); formal rebuild when ghcr pull is healthy. **Rotate leaked CAM keys.**

## Out of scope

- AUTH-07, billing, CDN public assets, multi-cloud replication, 成刊 PAGE/LETTER.
- Forcing production `OBJECT_STORE_BACKEND=s3` before migrate verification.
- Automated COS → volume reverse migrate.

## Verification

- `ruff` / `mypy app` — pass
- targeted pytest (s3/settings/migrate/qwen/export) — 27 passed
- full `pytest` — 127 passed
