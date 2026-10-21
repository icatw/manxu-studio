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
- 手验：两话有摘要后点续写 → 第三话；可选分镜路径。
