# 架构与技术选型

## 决策摘要

采用前后端分离的 TypeScript + Python 架构：

- **前端**：React、TypeScript、Vite、React Router、TanStack Query、Tailwind CSS、shadcn/ui。
- **后端**：Python 3.13、FastAPI、Pydantic v2、SQLAlchemy 2.x async、Alembic；uv 管理依赖。
- **数据库**：关系型数据库；优先 PostgreSQL。单元测试使用独立测试数据库。
- **图像存储**：S3 兼容对象存储；数据库保存资产元数据和对象键，不依赖供应商临时 URL。
- **API 契约**：`docs/api/openapi.yaml` 是人工维护的唯一契约源；前端从 YAML 生成类型，FastAPI 实现必须与 YAML 一致。

## 为什么选择 React + Vite

漫序是桌面优先的创作型单页应用，核心是项目工作区、分镜画布和检查器交互，不依赖搜索引擎收录或服务端页面渲染。Vite 官方模板直接支持 React/TypeScript，并提供开发期快速热更新；将 API、鉴权和模型密钥明确留在 FastAPI，避免再引入一套 Node 服务端业务层。

shadcn/ui 的组件源码安装到项目中，便于 AI 编程工具直接理解和局部修改组件，而不是把关键视觉层隐藏在黑盒主题包里。React Router 负责页面路由，TanStack Query 管理远端数据的读取、缓存、更新和生成任务轮询。

这一选型偏向显式、常见、可分层的模式，适合 AI 辅助开发时逐个功能实现、检查和回归。它不是因为“AI 专用框架”而选择，而是因为工具链成熟、文件边界清楚、官方文档可被工具读取。

## 前端职责

- 展示项目与创作步骤。
- 管理画布选择、面板展开、未提交输入等短期 UI 状态。
- 通过生成的 OpenAPI 类型化客户端访问 FastAPI。
- 使用 TanStack Query 缓存项目数据、提交更新，并以共享 `queryClient` 轮询生成任务（`lib/generation-task.ts` / `hooks/use-generation-task.ts`）。
- 选题/受众/画幅等 UI 选项集中在 `lib/catalogs.ts`；镜头与 API 枚举映射在 `lib/domain-mappings.ts`。
- Studio 持久化与 hydrate 在 `hooks/use-studio-persist.ts`；`StudioProvider` 只编排上下文。
- 不持有模型供应商密钥，不直接调用供应商 API。

## 后端职责

- 身份与项目访问控制（认证方式在部署阶段确认）。
- 项目、故事、角色、场景、分镜、版本和任务的业务规则（应用服务层，路由保持薄）。
- 调用文本/图像模型并适配供应商差异。
- 校验结构化输出、记录模型/提示词版本和结果。
- 处理异步图像任务、重试、对象存储和导出（任务状态无 `cancelled`；SLA 由 Settings 统一配置）。

## 推荐代码边界

```text
frontend/
  src/
    components/          # 页面与工作室 UI
    hooks/               # 账户、生成任务、Studio 持久化等
    services/            # 薄 API 编排；不持有供应商密钥
    lib/api/             # OpenAPI 生成类型与 HTTP 客户端
    lib/catalogs.ts      # 选题/受众/画风/画幅选项（单一来源）
    lib/domain-mappings.ts  # API↔展示枚举映射
    lib/generation-task.ts  # 任务查询与 Query 轮询
backend/
  app/
    api/                 # HTTP routers 与依赖（委托 services）
    schemas/             # Pydantic 请求/响应
    providers/           # 文本/图像/对象存储适配器
    tasks/               # 任务类型、注册表、handler、runtime
    services/            # 应用服务（projects/assets/storyboard/generations/auth…）+ 队列
    worker.py            # ARQ worker 入口
  tests/
docs/
```

生成任务通过 `tasks` 注册表分发；多步「故事起稿」使用 `story_pipeline` 在服务端编排，前端只提交一次并轮询。

## API 与类型同步

接口采用 YAML 先行。`docs/api/openapi.yaml` 是人工维护的规范；FastAPI 的 Pydantic 请求/响应模型实现该规范，不能反向把运行时生成的 `/openapi.json` 当作需求来源。前端从 YAML 生成 `frontend/src/lib/api/schema.d.ts`，禁止手工修改生成文件，并通过 `openapi-fetch` 或薄封装客户端使用生成类型。

CI 需要执行 YAML/OpenAPI 规范校验、从契约生成前端类型、检查 FastAPI 路由清单并对实际响应运行契约测试。FastAPI 的运行时 OpenAPI 输出只作为实现检查结果，不能覆盖源 YAML；仅对实现与契约的语义差异报错，需求关联等 YAML 扩展字段留在契约源。流程和评审门禁见 [API 契约与变更流程](../api/README.md)。

## 生成任务执行

HTTP 请求创建持久化任务并立即返回任务 ID。任务执行器负责供应商调用、轮询或回调、结果存储和状态更新；前端经 TanStack Query 按退避间隔查询任务（含 `RATE_LIMITED` 退避），后续如需更即时的状态再评估 SSE/WebSocket。队列使用 Redis + ARQ；作业超时、陈旧判定与轮询相关 SLA 由 `Settings` 统一提供。

## 配置与安全

- 模型、数据库、对象存储凭据只存在服务端环境变量或密钥管理服务；默认图像模型名等产品常量由配置/目录单源提供。
- `.env.example` 仅列变量名称和无效示例值，不放可用凭据。
- 上传图片验证大小、MIME 和文件内容；使用不可预测对象键。
- 记录模型调用元数据，不记录不必要的敏感信息。
- 本地开发默认允许前端开发服务器访问本地 API；生产 CORS 使用明确域名白名单。
- 模型配置与工作区业务数据以服务端账户数据为唯一事实源，浏览器不使用 localStorage 保存运行时配置。
- 演示数据只能通过 development 环境的显式 `uv run python -m app.cli.seed_demo --account-id <account-id>` 创建，生产启动不会自动 seed。

## 待决事项

- 文本和图像模型的具体供应商/模型与地域可用性。
- 部署平台、认证方案、PostgreSQL 托管和对象存储供应商。
- 生成任务是否需要服务端推送（当前以 Query 轮询为准）。
- 导出制作包的最终格式和是否支持多页排版。

## 技术参考

- [Vite 指南](https://vite.dev/guide/)
- [React Router 模式选择](https://reactrouter.com/start/modes)
- [shadcn/ui Vite 安装](https://ui.shadcn.com/docs/installation/vite)
- [TanStack Query 概览](https://tanstack.com/query/latest/docs/framework/react/overview)
- [FastAPI 首个步骤与 OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [FastAPI 并发与 async/await](https://fastapi.tiangolo.com/async/)
- [openapi-typescript](https://openapi-ts.dev/introduction)
- [uv 项目指南](https://docs.astral.sh/uv/guides/projects/)
- [Alembic 文档](https://alembic.sqlalchemy.org/en/latest/)
