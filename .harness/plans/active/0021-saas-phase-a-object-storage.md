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
- [ ] One-shot migrate script: volume files → COS + verify.
- [x] Tests: mock S3; settings validation; local backend still green in CI.
- [ ] Prod: create same-region bucket, IAM/key, cut over with rollback note in deploy docs.

## Out of scope

- AUTH-07, billing, CDN public assets, multi-cloud replication, 成刊 PAGE/LETTER.
- Forcing production `OBJECT_STORE_BACKEND=s3` before migrate verification.

## Verification

- `uv run --directory backend ruff check .` — pass
- `uv run --directory backend ruff format --check .` — pass
- `uv run --directory backend mypy app` — pass
- `uv run --directory backend pytest tests/test_s3_object_store.py tests/test_object_store_settings.py tests/test_qwen_image.py tests/test_export_png.py -q` — 24 passed
