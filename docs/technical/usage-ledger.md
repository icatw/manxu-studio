# 用量账本与请求关联（Phase 0 / 1）

> 更新：2026-10-22。支撑 SaaS 准备清单中的「用量与失败重试可追踪」；Phase 0/1 无独立用量 API；试用额度强制见计划 `0046`。

## 目标

1. 用结构化日志把 HTTP 请求与异步生成任务串起来。
2. 每次文本/图像 provider 往返写入 Postgres `usage_events`，作为后续额度与计费的真相源。

## 关联（Phase 0）

| 机制 | 说明 |
| --- | --- |
| `request_id` | `ApiResponseLoggingMiddleware` 生成；写入 `X-Request-ID`、响应 envelope，并进入 `contextvars` |
| `request_data._correlation.request_id` | `create_task` 创建任务时从 context 盖章，供 worker 恢复 |
| Worker context | `run_generation_task` 绑定 `account_id` / `project_id` / `generation_task_id` / `request_id` |
| JSON 日志字段 | `task_id`、`account_id`、`project_id`、`job_id`、`failure_id`、`call_kind`、`model`、token / `image_units`、`billable`、`outcome` 等 |

Worker 进程启动时调用与 API 相同的 `configure_api_logging`，保证 JSON Lines 输出。

**不记录**：Cookie、API Key、完整 prompt/响应体、图像内容。

## 账本表 `usage_events`（Phase 1）

每次 `generate_structured_text` / `generate_image` 结束后短事务插入一行（不跨 provider 等待持有连接）。

| 字段 | 含义 |
| --- | --- |
| `account_id` | 必填；缺省则只打 `provider_call_unattributed` 日志、不落库 |
| `project_id` / `generation_task_id` / `request_id` | 可空，尽量从 correlation 填充 |
| `call_kind` | `text` \| `image` |
| `provider` | `openai_compatible` / `qwen_async` / `openai_images` |
| `model` | 调用时的模型 ID |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | 文本 usage；兼容 `input_tokens`/`output_tokens`；缺失为 null |
| `image_units` | 图像成功为 `1`；文本为 null |
| `outcome` | `success` \| `failed` |
| `billable` | `outcome == success` |
| `latency_ms` / `error_code` | 观测辅助 |

索引：`(account_id, created_at)`、`(generation_task_id)`。

## 计费语义（冻结）

- **成功**（产出可用结果）→ `billable=true`。
- **失败** / 未产出可用结果 → 仍记账，`billable=false`。
- **自动恢复重试**若再次成功 → 再记一条可计费成功（反映真实供应商消耗）。
- 用户显式重试创建新 `generation_task` 时，成功调用同样各自记账。

后续产品额度规则可在此语义上聚合。**试用额度强制**见 PRD `QUOTA-01` 与计划 `0046`（本文件 Phase 0/1 不实现强制）。

## 后续 / `0046` 进度

- `billing_source`（`platform` \| `byok`）已落库；worker 从任务 `request_data.billing_source` 绑定 correlation。
- `platform` 模式入队前强制 Asia/Shanghai 自然日额度（文本次数 + 图像 `image_units`）；BYOK 只记账。
- `GET /model-config.quota` 为 UI 剩余额度视图（非第二套真相源）。

## 非目标

- 独立用量查询 HTTP API / Studio 用量页（设置页内嵌 `quota` 除外，见 `0046`）
- OpenTelemetry / Sentry / Prometheus
- 平台代付结算与套餐 SKU（试用额度 ≠ 收费）

## 实现入口

- 关联：`backend/app/core/correlation.py`、`middleware.py`、`services/generations.py`、`tasks/runtime.py`、`worker.py`
- 记账：`backend/app/services/usage.py`；调用点 `providers/openai_compatible.py`、`providers/image_dispatch.py`
- 迁移：`20261026_usage_events`
