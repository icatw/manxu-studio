# 测试策略调研：需求驱动的 API、E2E 与本地 Playground

## 结论

测试范围不能从现有路由、函数或组件反推。应先从已确认的 PRD、用户流程、OpenAPI 契约和安全风险整理可观察场景，再检查实现并补充技术边界测试。代码覆盖率用于发现未执行代码，不能代替需求覆盖。

本地 Docker Playground 负责提供可重复的依赖环境；pytest 和 Playwright 负责测试编排。首版不另建测试管理 UI。

## 防止测试跟着实现走

1. 先读取需求状态，只将 `confirmed` 需求纳入验收；`proposed` 和 `deferred` 先记录为待决，不因代码已经存在就视为产品承诺。
2. 按用户目标、数据边界和失败风险写测试场景，记录前置条件、外部操作、可观察结果和需求 ID；场景评审后再阅读相应实现。
3. 主流程通过公开 HTTP API 或真实浏览器交互验证，不调用内部 helper，也不把“某函数被调用”作为业务成功依据。
4. 使用独立 oracle 判断结果，例如另一个账户确实收不到资源、刷新后仍读到持久化数据、任务最终进入终态；避免用同一业务代码生成期望值。
5. 使用故障注入或 mutation testing 验证关键测试会失败，例如临时移除 owner 条件后，跨账户测试必须失败。

测试规格应先于实现测试；实现完成后再补充由代码细节发现的边界用例，并标注它们对应的风险或技术不变量。

## 测试范围矩阵

| 领域 | 必须验证的外部行为 | 主要测试层 |
| --- | --- | --- |
| API 契约 | 状态码、统一响应封套、校验错误、分页和非 JSON 下载 | 契约 + API |
| 账户与会话 | 登录、退出、过期/撤销会话、CSRF、OAuth state 一次性 | API 集成 + E2E |
| 邮箱验证码 | 自动注册/登录、过期、错误次数、重复消费、重发和限流、账户枚举 | API 集成 + E2E |
| 租户隔离 | A/B 对项目及全部子资源的查询、修改、删除和任务操作 | 双账户 API 安全测试 |
| 异步任务 | 排队、成功、失败、重试、重复提交、worker 重启恢复 | API + worker 集成 |
| 外部依赖故障 | 邮件、模型服务超时、限流、无效响应和不可用 | API/worker 集成 + 故障注入 |
| 创作主流程 | 登录、创建项目、编辑、生成、刷新恢复、失败提示和导出 | Playwright E2E |

具体功能及验收值以已确认 PRD 和冻结 OpenAPI 为准。当前文档只给出测试类别；验证码生命周期、限流阈值等产品参数应在对应需求/API 契约冻结时确认，不能由测试实现者自行决定。

## 分层与边界

- **单元测试**：适合纯业务规则、状态转换、验证码摘要比较、错误映射和重试策略；外部网络、数据库和浏览器不参与。
- **API 集成测试**：用 `pytest + httpx.AsyncClient` 经过真实 FastAPI 路由，连接独立 PostgreSQL/Redis，验证身份、持久化、副作用和响应契约。
- **E2E 测试**：用 Playwright 从浏览器操作真实前后端，覆盖少量高价值用户旅程；不把每个校验分支都堆进浏览器测试。
- **Provider 测试替身**：默认通过受控 fake HTTP 服务模拟 GitHub、SMTP 和模型服务的成功、超时及错误；避免常规测试依赖真实账户、密钥、费用或公网稳定性。真实供应商 smoke test 单独手动运行。
- **测试数据**：使用独立测试数据库和 run-scoped 数据；不得清理或复用开发数据库。并行测试应隔离数据库/schema 或使用唯一数据前缀。

## Docker Playground 方向

Docker Compose 提供 PostgreSQL、Redis、Mailpit、API、独立 worker 和可选 Playwright runner。服务带 healthcheck；测试开始前执行迁移，结束后保留失败日志和 Playwright trace。API 与 worker 日志通过 request ID 关联。

Playground 的固定入口建议为 `make playground-up`、`make playground-down`、`make test-unit`、`make test-api`、`make test-e2e` 和 `make test-all`。其中 test 命令由 pytest/Playwright 完成断言和编排；Compose 不承载测试结果管理逻辑。

Mailpit 仅捕获开发邮件，不投递真实收件人。Redis 和 PostgreSQL 使用专用测试配置；测试凭据通过环境变量注入，日志与失败工件不得包含 Cookie、验证码、OAuth code、模型 API Key 或完整请求正文。

## Skills 的职责

项目级测试设计 Skill 可固化需求追踪、代码盲测场景草拟、风险分类、独立 oracle 和 mutation 验证流程。Playwright 或 FastAPI 测试 Skill 可规范工具用法，但不能替代产品需求评审，也不能自动证明覆盖完整。Skill 产出的测试场景必须能追溯到需求 ID 或已记录风险。

## 待办事项

- [ ] 从确认后的 PRD 和用户流程建立需求 ID 到 API/E2E 场景的追踪矩阵；把 proposed/deferred 项单列，不混入验收范围。
- [ ] 为多账户注册范围确认测试前提和验收规则，覆盖双账户对项目、分镜、生成任务、图像版本与导出的隔离。
- [ ] 冻结邮件验证码时效、尝试上限、重发/限流规则及邮箱枚举策略，再据契约设计测试。
- [ ] 基于 Docker Compose 建立专用测试依赖环境、健康检查、迁移和固定 make 命令；确保不会连接或清理开发数据库。
- [ ] 增加 fake 邮件、GitHub 和模型 provider 场景，覆盖依赖失败、重试、重复请求和 worker 重启恢复。
- [ ] 建立 Playwright 核心用户旅程，失败时保存 trace、截图和脱敏日志。
- [ ] 对 owner 隔离、验证码单次消费和任务幂等执行 mutation/fault-injection 验证。
- [ ] 将需求场景覆盖、API operation 覆盖、关键风险覆盖与代码覆盖分别报告；不以单一覆盖率门槛代替验收。

## 完成标准

每个已确认需求都有至少一个可观察验收场景；每个高风险场景都有自动化测试或明确的人工验证安排；本地和 CI 使用同一套测试入口；测试数据、日志和并行运行彼此隔离。
