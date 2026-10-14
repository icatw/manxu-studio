# AI-native 工程工作流

## 研究结论

截至 2026-10-14，所查阅的官方工程实践与开源 spec-driven 工具呈现出这些共同做法；它们是可借鉴的工程模式，不是唯一标准：

- 仓库保存产品/领域知识、API 契约、架构决定、执行计划和进度，减少对聊天记录和个人记忆的依赖。
- `AGENTS.md` 只做入口索引和通用操作规则，任务按需读取具体文档，避免每次把全库塞进上下文。
- 规格先表达用户目标与验收；计划把跨层工作拆成任务；实现后运行自动检查并验证真实用户路径。
- 将边界和不变量变成类型、lint、契约检查和测试，而不是只写“请遵循架构”的说明。
- 记录代码审查、失败案例和人工反馈；只有反复出现的经验才升级为稳定规则或自动检查。
- 技能用于可重复的专门工作流，按需加载；项目刚开始时不复制大量通用技能或自建多 Agent 编排。

OpenAI 在 2026-02 的 harness engineering 文章强调仓库知识库作为 system of record、短 `AGENTS.md` 作目录、执行计划与机械校验；2026-09 的 Codex 文档建议随模型能力演进持续精简过长或冗余的指令。GitHub Spec Kit 的公开工作流是项目级原则一次维护，功能级 specify → plan → tasks → implement → converge。我们采用其可验证思想，但先使用仓库现有 Markdown/OpenAPI，不引入 Spec Kit CLI 的额外模板和命令体系。

## 本项目的知识分层

| 信息类型 | 唯一主来源 | 更新时机 |
| --- | --- | --- |
| Agent 通用工作规则 | 根目录 `AGENTS.md` | 通用操作约定改变时 |
| 用户目标和需求状态 | `docs/product/prd.md` | 用户确认、延期或调整范围时 |
| 页面和流程 | `docs/product/`、`docs/design/` | 用户路径/交互发生变化时 |
| 接口 wire contract | `docs/api/openapi.yaml` | API 契约评审时 |
| 架构原因 | `docs/technical/decisions/` | 关键技术决策产生或被替代时 |
| 领域含义 | `docs/knowledge/glossary.md` | 术语出现歧义或新增时 |
| 里程碑总体进度 | `.harness/status.md` | 阶段和阻塞变化时 |
| 当前多文件工作的执行状态 | `.harness/plans/active/` | 每次计划工作推进时 |
| 实际行为 | 源码、数据库迁移、自动检查和验收证据 | 每次实现变化时 |

## 功能变更闭环

1. **提出**：写清楚用户问题、目标、非目标和需求 ID，状态为 `proposed`。
2. **澄清与确认**：处理会改变数据结构、用户体验、权限、异步行为或成本的重要歧义。确认后把需求标为 `confirmed`。
3. **契约**：更新 OpenAPI YAML、错误/状态行为和示例；评审通过后冻结当前改动范围。
4. **计划**：跨多个模块的变更写 active plan，列出可验证任务和受影响边界；单文件小改动可直接做。
5. **实现**：按垂直切片完成 API、持久化、UI、错误/空/加载状态和可观测性，保持每步可运行。
6. **收敛**：运行相关 lint、类型检查、测试和契约检查；用户路径需要时在浏览器验证。失败就修正，或将明确阻塞记录到计划。
7. **文档与进度**：代码和文档在同一个变更中更新；完成条件满足后归档计划并推进项目状态。

## 需求确认门禁

- 没有 `confirmed` 状态和验收条件，不实现产品功能。
- API 变更必须关联 PRD requirement ID；前后端不得各自猜测字段。
- 契约或需求变化要说明兼容性、迁移、失败处理和人工可见反馈。
- `proposed` 可用于骨架评估或原型讨论，但不能描述成已交付能力。

## 进度记录规则

- 状态使用 `not-started`、`in-progress`、`blocked`、`done`，并记录阻塞原因/下一动作。
- 计划按任务逐项更新，不在结束时一次性补写虚假的过程记录。
- `done` 必须附验收或检查证据；无法运行的检查标记为未验证。
- 总览只写当前阶段、关键里程碑和阻塞；具体命令、决策和结果留在对应 active plan。

## 参考资料

- [OpenAI: Harness engineering（2026-02-11）](https://openai.com/index/harness-engineering/)
- [OpenAI: Rethinking skills and prompts（2026-09-11）](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
- [GitHub Spec Kit：Specify → Plan → Tasks → Implement → Converge](https://github.com/github/spec-kit)
- [OpenAI Skills 文档](https://developers.openai.com/api/docs/guides/tools-skills)
