# 项目状态

- 更新时间：2026-10-15
- 当前阶段：单机 VPS 一键部署（Compose + Caddy）已落地；演示录屏仍待做
- 代码阶段：邮箱/GitHub 登录、资源隔离、Redis/ARQ、providers/tasks 分层、应用服务层、定妆锁定、多话壳、连载层、Playwright E2E、playground、生成归属收口、多人角色参考图、VPS 部署 overlay 已接入

## 当前事实

- 生成架构：`providers/` + `tasks/` 注册表；应用服务 `projects/assets/storyboard/generations/model_config/auth`；路由保持薄。
- 契约：任务状态无 `cancelled`；生成 SLA（job/stale/poll）由 Settings 统一；默认图像模型单源。
- 前端：TanStack Query 共享 `queryClient` 轮询生成任务；`lib/catalogs`；`useCurrentAccount`；Studio hydrate/autosave 抽出。
- Phase 1 工作区对齐：PNG + 制作资料 JSON 导出；检查器可编辑构图/剧情作用；侧栏多话切换与新建；角色 `reference_locked` 定妆锁定；作品库卡片与派生 `cover_image_url`。
- Phase 2 连载层：PRD 解冻 SERIAL-01..04 与 PROJ-04；作品设定集；伏笔 CRUD；AI 季策划与 from-plan 创建；话摘要与 continuity 注入分镜；作品总览 Tabs；独立阅读页。
- 路由：`/projects` 作品库；`/projects/new` 策划；`/projects/:id` 总览；`/projects/:id/studio` 工作区；`/projects/:id/read/:episodeId` 阅读。
- API 资源名仍为 Project/Episode；产品文案为作品/话。迁移 head：`20261021_serial_layer`。
- Playwright：`frontend/e2e` + Mailpit 登录；`make test-e2e` / `make test-e2e-ai`；E2E 用 `docker-compose.e2e.yml` + `--profile local`。
- Playground：`docker-compose.playground.yml`（独立卷/端口、fake-llm、Mailpit）；`make test-api-playground` / `test-e2e-playground` / `test-playground`。
- 部署：`docker-compose.prod.yml` + Caddy；`./scripts/deploy.sh` / `make deploy`；本地 `start.sh` 使用 `--profile local`（Mailpit）；图像第一期仍为 `image-data` 卷（ADR-003）。
- 角色草稿：一次生成 2–6 人阵容并为每人出参考图（定妆锁定保留）。默认 `cast_mode=append`（同名跳过、不删孤儿）；`replace` 仅危险整队重建。
- 本话生成：已有作品角色库时默认 `regenerate_characters=false` 复用；故事页可「补充角色」追加或「重建作品角色库」。
- 单资产重生：角色/场景卡片可「重生设定」「重出参考图」；支持批量补缺失参考图（`character_reference_images` / `scene_reference_images`）。
- 计划：`.harness/plans/completed/0018-project-cast-reuse.md`；`.harness/plans/completed/0017-per-asset-regen.md`；`.harness/plans/completed/0014-multi-character-reference-images.md`；`.harness/plans/completed/0015-vps-compose-caddy-deploy.md`。

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
| 生成归属收口 | 完成 | hydrate 合并、resume、停止跟踪、idempotency（#4） |
| 发布与交付 | 进行中 | VPS 一键部署已具备；演示录屏与托管对象存储仍待 |

## 下一步

1. 在真实 VPS + 域名上跑通 `./scripts/deploy.sh` 冒烟（登录、生成、图片持久）。
2. 配置 GitHub OAuth 后完成双账户隔离浏览器验证。
3. 演示录屏；后续再规划对象存储与托管 Postgres。
