# 项目状态

- 更新时间：2026-10-15
- 当前阶段：架构债清理与独立 Docker playground 均已合入 main
- 代码阶段：邮箱/GitHub 登录、资源隔离、Redis/ARQ、providers/tasks 分层、应用服务层、定妆锁定、多话壳、连载层、Playwright E2E、playground Compose/fake-llm 已接入

## 当前事实

- 生成架构：`providers/` + `tasks/` 注册表；应用服务 `projects/assets/storyboard/generations/model_config/auth`；路由保持薄。
- 契约：任务状态无 `cancelled`；生成 SLA（job/stale/poll）由 Settings 统一；默认图像模型单源。
- 前端：TanStack Query 共享 `queryClient` 轮询生成任务；`lib/catalogs`；`useCurrentAccount`；Studio hydrate/autosave 抽出。
- Phase 1 工作区对齐：PNG + 制作资料 JSON 导出；检查器可编辑构图/剧情作用；侧栏多话切换与新建；角色 `reference_locked` 定妆锁定；作品库卡片与派生 `cover_image_url`。
- Phase 2 连载层：PRD 解冻 SERIAL-01..04 与 PROJ-04；作品设定集；伏笔 CRUD；AI 季策划与 from-plan 创建；话摘要与 continuity 注入分镜；作品总览 Tabs；独立阅读页。
- 路由：`/projects` 作品库；`/projects/new` 策划；`/projects/:id` 总览；`/projects/:id/studio` 工作区；`/projects/:id/read/:episodeId` 阅读。
- API 资源名仍为 Project/Episode；产品文案为作品/话。迁移 head：`20261021_serial_layer`。
- Playwright：`frontend/e2e` + Mailpit 登录；`make test-e2e` / `make test-e2e-ai`；E2E 用 `docker-compose.e2e.yml` 把 SMTP 指到 Mailpit。
- Playground：`docker-compose.playground.yml`（独立卷/端口、fake-llm、Mailpit）；`make test-api-playground` / `test-e2e-playground` / `test-playground`；前端映射 `15174`；`ALLOW_PRIVATE_MODEL_BASE_URLS` 仅 playground 开启。
- 计划：`.harness/plans/completed/0013-architecture-debt-cleanup.md`；`.harness/plans/completed/0013-playground-api-e2e.md`。
- 验证：架构债清理合入后 backend/frontend CI 绿；playground API 4 passed + serial-core Playwright 1 passed（合入前）。

## 阶段与进度

| 阶段 | 状态 | 完成条件 |
| --- | --- | --- |
| 产品文档与初版 API 草案 | 完成 | 简报、PRD、流程、页面说明、领域模型、AI 管线和 YAML 草案已存在 |
| 需求确认与接口冻结 | 完成 | 核心工作区 + 连载层需求确认；OpenAPI 同步 |
| 工程骨架 | 完成 | 前后端可启动、锁文件/迁移/CI/契约校验就绪 |
| 创作主流程演示切片 | 完成 | 项目 → 故事 → 角色/场景 → 分镜 → 图像版本 → 预览/PNG 导出 |
| 多账户与队列 | 实现完成 | 邮箱/GitHub、隔离、Redis/ARQ |
| 自定义文本与 Qwen Image | 真实账户端到端验证完成 | 文本与图像生成持久化 |
| 生成架构分层 | 完成 | providers + task registry 合入 main（#1） |
| v0 工作区体验对齐 | 完成 | 导出双格式、构图字段、多话壳、定妆锁定、库卡片 |
| 连载层 | 完成 | 策划/伏笔/摘要/设定集/阅读页 + Playwright 核心与 live AI E2E |
| 架构债清理 | 完成 | 服务层抽取、cancelled 移除、Query 轮询、catalogs、Studio 拆分（#2） |
| Playground 测试环境 | 完成 | 独立 Compose + fake-llm API 套件 + Playwright hang + CI job（#3） |
| 发布与交付 | 未开始 | 部署、演示录屏、运行说明 |

## 下一步

1. 确认 CI `playground` job 在 main 上稳定。
2. 配置 GitHub OAuth 后完成双账户隔离浏览器验证。
3. 验证生成失败重试与 worker 重启恢复。
