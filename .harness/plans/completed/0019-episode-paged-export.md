# 0019 — 本话分页 PNG ZIP 导出

## Goal
本话导出支持按页高自动分页为 ZIP；跨话合集仅记 PRD proposed。

## Done
- [x] PRD EXP-01 扩展 + EXP-02 proposed；user-flows；OpenAPI `png_zip`
- [x] backend `_pack_pages` + `render_png_zip`；下载 `.zip` Content-Type
- [x] 工作室「长图 / 分页 ZIP / 制作资料」
- [x] pytest + typecheck

## Verification
- `uv run --directory backend pytest tests/test_export_png.py tests/test_export_download.py`
- `pnpm --dir frontend api:lint` / `api:types` / `typecheck`
