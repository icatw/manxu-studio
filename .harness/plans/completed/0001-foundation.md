# 计划 0001：项目工程骨架

- 状态：`completed`
- 创建日期：2026-10-14
- 依赖：ADR-001 被确认；ADR-002 已确认。
- 当前进度：工程骨架和验收项已完成，计划已归档

## 目标

建立可由人和 coding agent 共同工作的前后端项目骨架，能够本地启动、运行质量检查、验证 OpenAPI 契约，并让后续功能在清晰的边界内逐步实现。

## 范围

- 初始化 Git 和前端 React/TypeScript/Vite 应用。
- 初始化 FastAPI 应用、uv 项目和锁文件。
- 配置 PostgreSQL 开发服务和 Alembic 起始结构。
- 配置 OpenAPI lint 与 TypeScript 类型生成。
- 增加最小 CI、环境变量示例和本地运行说明。
- 不接入真实文本/图像模型，不实现未确认产品需求。

## 任务

- [x] 初始化前后端目录、包管理器和严格类型检查。
- [x] 建立 FastAPI health/version 路由与基本错误格式。
- [x] 加入数据库连通配置和 Alembic，不在启动时隐式改写生产 schema。
- [x] 加入 YAML 规范校验、OpenAPI TypeScript 类型生成和路由契约检查。
- [x] 配置 lint、类型检查、单元/契约测试与 CI 命令。
- [x] 编写本地启动、迁移、验证和环境变量说明。

首个产品功能切片开始前，另行确认 PRD 首批需求并冻结对应 API；这不是初始化工程骨架的前置条件。

## 验收

- [x] 新环境按 README 操作可启动前端、API 和数据库。
- [x] OpenAPI YAML 校验通过，前端 API 类型可从契约重复生成且无手工漂移。
- [x] API health/version 路由有契约定义和自动验证。
- [x] 所有代码质量命令可从仓库执行，CI 执行相同质量门禁。
- [x] 没有真实密钥，环境变量示例使用本地开发占位值。

## 执行记录

完成记录（2026-10-14）：

- 使用 pnpm 和 uv 建立锁定依赖；本地 Python 3.13 由 uv 管理。
- `make check`、`make test` 和前端 production build 通过；后端 3 项测试、前端 1 项测试通过。
- `docker compose config`、PostgreSQL 健康检查、`alembic upgrade head` 和 `/api/v1/health`、`/api/v1/version` 均验证通过。
- Playwright 桌面/移动视口检查通过，页面能连接 API，无浏览器控制台错误。
- 本地 PostgreSQL 使用 55442 端口，避开已有服务占用的 5432/5433。
- 已知边界：产品需求和业务 API 仍为 proposed/draft；认证、模型供应商、worker、部署与对象存储尚未决定。
