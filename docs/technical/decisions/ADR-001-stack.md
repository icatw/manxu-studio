# ADR-001：应用技术栈

- 状态：`accepted`
- 日期：2026-10-14
- 决策人：依据用户授权完成前端调研后记录

## 背景

漫序是桌面优先的交互式创作工作台，核心界面是项目导航、分镜画布和属性检查器。它没有首屏 SEO/SSR 需求。用户指定后端使用 Python FastAPI；HTTP API 采用 YAML 先行。

## 决定建议

### 前端

- React + TypeScript strict + Vite。
- React Router 负责页面路由。
- TanStack Query 负责服务端数据、缓存、更新和生成任务轮询。
- Tailwind CSS + shadcn/ui，组件源码留在仓库内，便于直接检查和修改。
- `openapi-typescript` + `openapi-fetch` 从 `docs/api/openapi.yaml` 生成并消费 API 类型。
- pnpm 管理前端依赖；不因单个前端应用提前建立复杂 workspace/monorepo 抽象。

选择 Vite SPA 而不是 Next.js：FastAPI 已承担服务端职责，当前产品不需要 Node 服务端渲染、SEO 或 Next.js API 路由。React/Vite 的常见文件结构、成熟生态和可见组件源码更适合 AI 编程工具逐步实现并由人审阅。

### 后端

- Python 3.13（部署平台确认后锁定运行时版本）+ FastAPI + Pydantic v2。
- uv 管理依赖与跨平台锁文件。
- SQLAlchemy 2.x async + Alembic；PostgreSQL 作为持久化数据库。
- pytest + HTTPX 做后端测试，Ruff 做 lint/format；模型供应商和对象存储通过后端 provider 适配层隔离。

### 运行与生成任务

- 文本/图像生成使用持久化任务记录，API 返回任务 ID，客户端查询状态。
- 不在请求进程中用内存任务承载需要跨重启恢复的图像生成。
- 消息队列/worker 产品、部署方式和图片对象存储供应商暂不锁定；先依据并发、重试、供应商回调和运维环境选择。

## 候选方案比较

| 方案 | 优点 | 本项目代价 | 结论 |
| --- | --- | --- | --- |
| React + Vite SPA | 桌面工作台直观；FastAPI 单独提供后端；交互依赖少 | SEO/SSR 需另加方案，但当前不需要 | 推荐 |
| Next.js | 全栈约定多，生态和 AI 示例丰富 | 与 FastAPI 并存会出现 Node/Python 双服务端边界；API/BFF 职责可能重复 | 暂不选 |
| Vue + Vite | 单文件组件边界清楚，Vite 支持成熟 | React 的组件/UI 资源与 AI 代码样例覆盖更广这一点是判断性优势，不是功能限制 | 可用备选 |

## 后果与待确认

- 这套选择减少服务端职责重复，接口和业务逻辑统一由 FastAPI 管理。
- 前端类型从 API 契约生成；不能另手写一份接口类型。
- 长任务仍需持久 worker 和稳定文件存储，具体运行设施留到部署决策阶段确定。
- 前端栈按本次调研结论采用 React + Vite，后端按用户指定采用 FastAPI；部署和异步任务设施仍待实际环境约束确认。

## 参考资料（查阅于 2026-10-14）

- [Vite 指南](https://vite.dev/guide/)
- [React Router 模式选择](https://reactrouter.com/start/modes)
- [shadcn/ui Vite 安装](https://ui.shadcn.com/docs/installation/vite)
- [TanStack Query 概览](https://tanstack.com/query/latest/docs/framework/react/overview)
- [FastAPI 多文件应用](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [uv 项目指南与锁文件](https://docs.astral.sh/uv/guides/projects/)
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic 文档](https://alembic.sqlalchemy.org/en/latest/)
- [pnpm 工作区](https://pnpm.io/workspaces/)
- [openapi-typescript](https://openapi-ts.dev/introduction)
