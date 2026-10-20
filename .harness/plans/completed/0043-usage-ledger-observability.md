# 0043 — 用量账本与可观测性（Phase 0+1）

## 目标

HTTP↔worker 关联 + `usage_events` 落库；无公开 API / UI / OTel。

## 完成

- [x] `correlation` contextvars；middleware / create_task / runtime / worker JSON 日志
- [x] `JsonLogFormatter` 扩展 task / usage 字段
- [x] 迁移 `20261026_usage_events` + `UsageEventRecord` + `services/usage.py`
- [x] 文本/图像 provider wrapper 记账与 `provider_call_*` 日志
- [x] 文档 `docs/technical/usage-ledger.md`；saas-readiness / status 更新
- [x] 单测 `backend/tests/test_usage_ledger.py`

## 验证

```sh
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
uv run --directory backend mypy app
uv run --directory backend pytest tests/test_usage_ledger.py tests/test_api_responses.py -q
```

## 非目标（后置）

预估用量、额度强制、查询 API、OTel。
