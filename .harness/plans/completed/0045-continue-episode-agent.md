# 0045 — 续写编排（无对话框 Agent）

## Goal

「续写下一话」走服务端可恢复工具链：摘要门禁 → 建话 →（可选）分镜。无聊天 UI。

## Done when

- [x] SERIAL-AGENT-01 `confirmed`；OpenAPI continue-episode 契约
- [x] `continue_episode` handler + frontier 409 + checkpoint
- [x] 总览 ▾：仅建话 / 建话并分镜；工作室「+」仅建话
- [x] pytest（含 registry）+ frontend typecheck/test/build

## Notes

- 默认不出图、不种泡。
- 手验（2026-10-21 playground `:15174` / `:8001`）：
  - API：`tests/playground/test_continue_episode_workflow.py` 通过（409 → 仅建话 → 建话+分镜）。
  - UI：总览「续写下一话」toast「已续写下一话」；▾「建话并生成分镜脚本」→ 第 3 话 + 8 格；截图 `var/qa-screenshots/continue-agent/`。
  - fake-llm：continuity 含「前情摘要」时曾误返 summary；已优先匹配分镜 `panels`。
