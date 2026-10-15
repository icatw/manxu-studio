# 0018 — 作品角色库复用与追加

## Goal
本话默认复用作品角色；append 不覆盖/不删旧；replace 仅危险入口；修确认框与侧栏误导。

## Done
- [x] docs + openapi + types（ASSET-01/02、SB-01、user-flows；`cast_mode` / pipeline cast modes）
- [x] backend append/replace（characters/scenes handlers；空数组允许）
- [x] frontend defaults + IA（故事页复用/追加/危险重建；侧栏「作品角色/场景」）
- [x] tests + verify（pytest append/replace；openapi lint；tsc）

## Verification
- `uv run --directory backend pytest tests/test_workspace_tasks.py tests/test_character_reference_lock.py` — pass
- `pnpm --dir frontend api:lint` / `tsc --noEmit` — pass
