# 项目知识库

知识库只保留能帮助后续工作理解领域、约束和决策的长期信息。代码和自动化检查是运行行为的最终依据；文档解释意图和边界。

## 入口

- [产品与技术文档总览](../README.md)
- [产品术语表](glossary.md)
- [架构与技术决策](../technical/decisions/)
- [AI 生成管线](../technical/ai-pipeline.md)
- [API 契约与变更流程](../api/README.md)
- [AI-native 工程工作流](../../.harness/ai-native-workflow.md)
- [当前进度](../../.harness/status.md)
- [执行计划](../../.harness/plans/README.md)

## 维护规则

- 一类事实只保留一个主来源，其他页面链接过去。
- 新决定进入 ADR，标记 `proposed`、`accepted`、`superseded` 或 `rejected`，附日期、原因和影响。
- 验证状态与发布日期易变，注明日期并在变更时更新。
- 运行时行为优先以代码、OpenAPI 契约和自动检查为准；发现不一致时修正文档或实现，不留下两套事实。
- 每项领域术语给出定义和不包含的意思，避免故事、剧集、分镜、画格混用。
