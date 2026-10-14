# Harness 工作区

`.harness/` 保存 coding agent 的项目工作流、当前进度和可恢复执行计划。根目录 [`AGENTS.md`](../AGENTS.md) 是简短入口；产品和技术事实仍以 [`docs/`](../docs/README.md) 中的 PRD、OpenAPI、架构和领域资料为准。

## 内容

- [AI-native 工作流](ai-native-workflow.md)：需求门禁、变更闭环与文档职责。
- [项目状态](status.md)：唯一的阶段、阻塞和下一步总览。
- [计划管理约定](plans/README.md)：active/completed 计划规则。
- `plans/active/`：正在推进或等待前置决策的多文件工作。
- `plans/completed/`：已完成并归档的工作计划。

## 维护边界

- `.harness/` 管理 agent 如何工作和工作到哪里，不复制产品需求或 API schema。
- 产品范围看 `docs/product/prd.md`；接口事实看 `docs/api/openapi.yaml`；技术选择看 `docs/technical/decisions/`。
- 每个计划的进度随实际工作逐项更新；总体阶段只更新 `status.md`。
