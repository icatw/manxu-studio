# Model eval harness（离线、opt-in）

对比文本+图像生成轨迹（plan → 角色/定妆 → 场景 → 分镜 → 选格出图），**不进普通 CI**，不改产品默认模型。

## 配置

| id | 文本 | 图像 |
| --- | --- | --- |
| `baseline` | Qwen（OpenAI 兼容） | Qwen Image 异步 |
| `agnes-full` | Agnes | Agnes Image |
| `mix-text` | Agnes | Qwen Image |
| `mix-image` | Qwen | Agnes Image |

环境变量（按所选配置需要）：

```bash
export MODEL_EVAL_LIVE=1
export QWEN_TEXT_API_KEY=...
export QWEN_IMAGE_API_KEY=...   # 可与文本同钥
# 可选覆盖：QWEN_TEXT_BASE_URL / QWEN_TEXT_MODEL / QWEN_IMAGE_BASE_URL / QWEN_IMAGE_MODEL

export AGNES_API_KEY=...
# 可选：AGNES_BASE_URL AGNES_TEXT_MODEL AGNES_IMAGE_MODEL
```

## 运行

```bash
# 小烟：单配置 + 单 case + 跳过图像
make model-eval ARGS='--config baseline --case A-duo --trials 1 --skip-images'

# 完整对照（费时费钱）
make model-eval ARGS='--trials 2'

# Agnes 图像参考臂（Arm B，勿与 baseline 直接横比分）
make model-eval ARGS='--config agnes-full --with-agnes-refs --case A-duo --trials 1'
```

产物：`var/model-eval/runs/<run_id>/`

- `manifest.json` / `summary.json` / `summary.csv`
- `<config>/<case>/trial-NN/`：阶段 JSON、图像、`score.json`
- `blind_scorecard.csv`：打乱文件名后人工盲评

## 判定（建议）

相对 `baseline`：`pass@k` 不降、盲评角色一致均值 ≥ baseline，再考虑可选 preset；图像公平对比用 **Arm A**（默认纯文生图）。

出图提示含强无字约束（工牌/霓虹/UI 等）；每次 live 用新 `--run-id`，勿覆盖已有 `var/model-eval/runs/<id>/`。

## 单测

```bash
uv run --directory backend pytest tests/test_model_eval_scoring.py -q
```
