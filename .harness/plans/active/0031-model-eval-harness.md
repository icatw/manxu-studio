# 0031 — 模型测评脚手架（文本+图像轨迹）

## Goal

落地轻量、opt-in 的离线测评：固定 case × 多配置 × 多 trial，自动 schema/业务分 + 盲评表；不引入第三方评测框架；不进普通 CI；不改产品默认模型。

## Decisions

- 无 Braintrust / Promptfoo：自研 `scripts/model_eval` + `var/model-eval/`。
- 轨迹对齐生产：plan → 角色 → 定妆图 → 场景 → 场景图 → 分镜 → 选格出图（含一格小改）。
- 配置：`baseline` / `agnes-full` / `mix-text` / `mix-image`。
- 图像公平臂：默认 A（纯文生图）；`--with-agnes-refs` 启用 B（Agnes 多图参考，不与 baseline 直接横比）。
- Live 调用需 `MODEL_EVAL_LIVE=1` + 环境变量密钥；`runs/` gitignore。

## Acceptance

- [x] 三个冻结 fixture + 盲评 CSV 模板
- [x] Runner 写出 manifest / stages / summary scores
- [x] 纯函数打分有单测（无 live）— 5 passed
- [x] Makefile `model-eval` + README 用法
- [ ] 人工跑一轮 live 并填盲评（操作项，非代码）

## Verification

- [x] `uv run --directory backend pytest tests/test_model_eval_scoring.py -q` → 5 passed
- [ ] Live：`make model-eval ARGS='--config baseline --case A-duo --trials 1'`（需密钥）
