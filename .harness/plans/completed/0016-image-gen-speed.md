# 0016 — 图像生成加速（默认 3.0 / 关参考图 prompt_extend / 角色参考图并行）

## Goal
缩短 `story_pipeline` / `character_draft` 角色参考图耗时，且仍走现有 DashScope Qwen Image 接入。

## Decisions
1. 默认图像模型改为 `qwen-image-3.0`（pro 仍在 allowlist，可选手动切回）。
2. 角色/场景参考图调用传 `prompt_extend=False`；分镜终稿图保持默认 `True`。
3. 角色参考图按 `IMAGE_MODEL_CONCURRENCY`（默认 2）有限并行；session 检查点回调与 ORM 写回用同一把 `asyncio.Lock`。

## Steps
- [x] 改 `DEFAULT_IMAGE_MODEL` / env 示例 / 前端初始默认
- [x] `generate_image` 增加 `prompt_extend` 参数
- [x] 角色/场景参考图关 extend；角色参考图并行
- [x] 补测试并跑相关 pytest / ruff

## Verification
- character handler 断言 `prompt_extend=False` 且多角色仍全部出图
- qwen_image 断言请求体 `prompt_extend` 随参数变化
- `ruff` + `mypy` + 相关 pytest：22 passed

## Note
已有账户的 `account_model_configs.image_model` 不会自动改写；需在设置里切到 `qwen-image-3.0`，或更新该行。
