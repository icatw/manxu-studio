# 0021 SaaS Phase A — object storage (COS)

## Goal

Replace Docker `image-data` volume dependency for production assets with Tencent COS via an S3-compatible `ObjectStore`, per ADR-004. Keep local/CI on `LocalObjectStore`.

## Gate

- [ ] Confirm **INFRA-02** in `docs/product/prd.md` (`proposed` → `confirmed`) before merging production cutover.
- [ ] OpenAPI / settings / ownership download contract updated YAML-first if response shape changes (e.g. signed URL field).

## Decisions

- Provider: Tencent COS; client: S3-compatible (configurable endpoint). ADR-004 `accepted` 2026-10-16.
- Bucket private; no public CDN as default read path in this phase.

## Work

- [x] ADR-004 + architecture / PRD cross-links.
- [ ] Settings + `.env*.example` for `OBJECT_STORE_BACKEND` / S3_* .
- [ ] `S3ObjectStore` implementing `ObjectStore`; wire Qwen download + export + asset GET.
- [ ] Persist object key (and content-type/size) where only local path was implied; migration if needed.
- [ ] Ownership-checked download: presigned GET and/or existing proxy stream.
- [ ] One-shot migrate script: volume files → COS + verify.
- [ ] Tests: mock S3; ownership denial; local backend still green in CI.
- [ ] Prod: create same-region bucket, IAM/key, cut over with rollback note in deploy docs.

## Out of scope

- AUTH-07, billing, CDN public assets, multi-cloud replication, 成刊 PAGE/LETTER.

## Verification

- Record commands and evidence here when implementation starts.
