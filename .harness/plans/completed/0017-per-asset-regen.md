# 0017 — 单资产重生 + 孤儿清理 + 滚动修复

## Goal
按完整档：单角色/场景可重生文本与/或参考图；全量重生删除孤儿；修复角色页无限滚动。

## Acceptance
- PRD ASSET-01/02 + OpenAPI 已更新；前端类型已生成
- 全量角色重生删除未返回角色并 scrub 分镜 character_ids
- 卡片可 text+image / image_only；角色页可批量补缺失参考图
- 角色页 textarea 限高，不再异常拉长滚动

## Steps
- [x] docs + openapi + types
- [x] backend handlers
- [x] frontend actions + scroll
- [x] tests + verify

## Verification
- pytest workspace/character/registry: 14 passed
- ruff + mypy on touched backend modules: clean
- frontend `pnpm typecheck`: clean
