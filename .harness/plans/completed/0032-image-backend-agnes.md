# 0032 — 图像后端可选（Qwen async / OpenAI images，含 Agnes 预设）

## Goal

账户可选择图像后端与服务端下发的系统预设（含 Agnes），不在前端硬编码供应商名/模型 ID；生成路径按 `image_backend` 分发。

## Decisions

- `image_backend`: `qwen_async` | `openai_images`（显式字段，不用模型名推断）
- 预设 / allowlist 来自 Settings（`MODEL_SYSTEM_PRESETS` JSON 可覆盖默认）
- OpenAI 风格同步出图；checkpoint resume 若无本地资产则重提

## Acceptance

- [x] PRD MODEL-02/03 更新 + OpenAPI
- [x] migration `image_backend`
- [x] openai_images provider + dispatch
- [x] 设置页多预设 + 按 backend 过滤模型列表
- [x] 单测 / 类型生成

## Verification

- [x] `pytest tests/test_model_presets.py tests/test_openai_images.py` → 7 passed
- [x] mypy on touched modules; `pnpm api:types` + typecheck; `App.test.tsx` 2 passed
- [ ] 本地迁移 `alembic upgrade head` 后用设置页选 Agnes 预设做连通性手验
