# 0046 — 模型模式：平台默认 Agnes + BYOK（Qwen / 自备 Agnes）+ 试用额度

## Goal

新用户默认走运营方托管 Agnes（零填 Key）；进阶可选自备百炼或自备 Agnes。仅平台模式扣试用额度。

## Requirements

- `MODEL-04` / `QUOTA-01`：`confirmed`（PRD）
- 契约：`docs/api/openapi.yaml` — `ModelMode`、`ModelConfig.model_mode` / `platform_available` / `quota`、`ModelConfigUpdate.model_mode`

## Decisions

| 项 | 选择 |
| --- | --- |
| 主叙事 | 平台默认额度为主；BYOK 为进阶 |
| 模式 | `platform` \| `byok_qwen` \| `byok_agnes`（文本+图像同模式） |
| 平台密钥 | 服务端 env/密钥管理；永不入账户表、永不回显 |
| 额度真相源 | `usage_events`（`billable=true`）；仅 `platform` 强制 |
| 超额 | 入队前拒绝；引导切 BYOK |
| 多账号农场 | **不做** |

## Done when

- [x] 后端：平台凭证配置；`model_mode` 持久化；`require_*_model` 按模式解析密钥
- [x] 后端：平台模式入队前额度强制 + 全站上游护栏（并发任务数）
- [x] OpenAPI 类型生成；设置页三档 UI；默认模式无 Key 输入
- [x] GET 返回 `quota`；超额 402
- [x] 单测：mode/quota/resolve；全量 unit `230 passed`
- [x] playground 手验（2026-10-22）：`test_model_mode_platform` + continue/serial 走 platform 默认共 4 passed；UI 设置页三档 +「今日剩余」截图 `var/qa-screenshots/model-mode/`
- [x] 归档本计划

## Quota slice (pinned)

- 窗口：Asia/Shanghai 自然日（见 `platform_quota.shanghai_day_bounds`）
- 计数：`billing_source=platform` 且 `billable=true`；文本按次数、图像按 `image_units` 分项
- 上限：`PLATFORM_QUOTA_TEXT_PER_DAY` / `PLATFORM_QUOTA_IMAGE_PER_DAY`（默认 40/30；0=不限）
- `usage_events.billing_source` 列已加（迁移 `20261027_model_mode_quota`）

## Non-goals

- 付费套餐 SKU / 支付
- 任意第三方 Base URL 作为主 UI
- Agnes 多账号 Key 池轮询
- 生产解冻（仍按 status 冻结）

## Notes

- 实现前确认生产/ playground 的 `PLATFORM_*` / Agnes env 命名与密钥注入路径。
- 与 `0045` playground 测试、fake-llm 修复可并行提交，互不阻塞。
