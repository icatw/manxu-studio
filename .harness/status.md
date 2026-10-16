# 项目状态

- 更新时间：2026-10-16
- 当前阶段：公网演示与 VPS（nginx 边缘）已落地；**下一工程重点为 SaaS 稳托**；**完整漫画 / 成刊为长期目标（规划文档已写入，未授权实现）**
- 代码阶段：邮箱/GitHub 登录、资源隔离、Redis/ARQ、providers/tasks 分层、应用服务层、定妆锁定、多话壳、连载层、Playwright E2E、playground、生成归属收口、多人角色参考图、VPS nginx overlay、合集导出与摘要门禁已接入

## 当前事实

- 生成架构：`providers/` + `tasks/` 注册表；应用服务 `projects/assets/storyboard/generations/model_config/auth`；路由保持薄。
- 契约：任务状态无 `cancelled`；生成 SLA（job/stale/poll）由 Settings 统一；默认图像模型单源。
- 前端：TanStack Query 共享 `queryClient` 轮询生成任务；`lib/catalogs`；`useCurrentAccount`；Studio hydrate/autosave 抽出。
- Phase 1 工作区对齐：PNG + 制作资料 JSON 导出；检查器可编辑构图/剧情作用；侧栏多话切换与新建；角色 `reference_locked` 定妆锁定；作品库卡片与派生 `cover_image_url`。
- Phase 2 连载层：PRD 解冻 SERIAL-01..04 与 PROJ-04；作品设定集；伏笔 CRUD；AI 季策划与 from-plan 创建；话摘要与 continuity 注入分镜；作品总览 Tabs；独立阅读页。
- 路由：`/projects` 作品库；`/projects/new` 策划；`/projects/:id` 总览；`/projects/:id/studio` 工作区；`/projects/:id/read/:episodeId` 阅读。
- API 资源名仍为 Project/Episode；产品文案为作品/话。迁移 head：`20261022_export_project_scope`。
- Playwright：`frontend/e2e` + Mailpit 登录；`make test-e2e` / `make test-e2e-ai`；E2E 用 `docker-compose.e2e.yml` + `--profile local`。
- Playground：`docker-compose.playground.yml`（独立卷/端口、fake-llm、Mailpit）；`make test-api-playground` / `test-e2e-playground` / `test-playground`。
- 部署：`docker-compose.prod.yml` + 共用机 `docker-compose.prod.nginx.yml`（禁 Caddy）；公网 `manxu.icatw.site`；私有运维脚本在 gitignored 的 `var/ops-private/`。图像第一期仍为 `image-data` 卷（ADR-003）。
- 角色草稿：一次生成 2–6 人阵容并为每人出参考图（定妆锁定保留）。默认 `cast_mode=append`；`replace` 仅危险整队重建。
- 本话生成：已有作品角色库时默认 `regenerate_characters=false` 复用。
- 导出：本话长图/分页 ZIP；作品总览「导出合集」（ZIP/PDF，EXP-02）。
- 连载：第 N 话生成分镜前须有第 N-1 话非空摘要（409）。
- **长期目标文档**：`docs/product/roadmap-complete-comic.md`；PRD 中 `PAGE-*` / `LETTER-*` / `PUBLISH-*` / `INFRA-02` 均为 `proposed`。

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
| Playground 测试环境 | 完成 | 独立 Compose + fake-llm API 套件 + Playwright + CI job（#3） |
| 生成归属收口 | 完成 | hydrate 合并、resume、停止跟踪、idempotency（#4） |
| 发布与交付 | 基本完成 | 公网可访问、演示录屏与提交材料已具备；CI 与运维脚本持续收口 |
| SaaS 稳托（对象存储等） | 未开始 | 见 `saas-readiness.md`；建议作下一工程阶段 |
| **完整漫画 / 成刊层** | **长期目标（规划）** | 见 `docs/product/roadmap-complete-comic.md`；需求仍为 `proposed` |

## 下一步

1. **工程近期**：对象存储（INFRA-02 草案评审）、AUTH-07、生产邮件与配额；更新 SaaS 清单与现状对齐。
2. **长期目标（不抢近期排期）**：成刊 MVP — 页模型 + 条漫排版 + 气泡层 + 成稿导出（PAGE / LETTER / PUBLISH）；确认需求并 YAML-first 后再开计划。
3. 保持 CI 绿灯；私有运维保留在 `var/ops-private/`。
