# 项目状态

- 更新时间：2026-10-20
- 里程碑 tag：`v0.1.0-storyboard`（commit `310d85e`）— 分镜/画格工作台 + 生产 COS 切流快照
- **生产部署冻结**：tag 之后默认**不**向 `manxu.icatw.site` 推送应用更新，直至产品规划与对外表述对齐、并明确解除冻结。线上继续跑该里程碑对应能力；仅紧急热修（安全/数据损坏）可破例，且须单独记录。
- 当前阶段：公网演示保持 tag 态；**A1–A3 已交付**；**A′ 已收口**（`0028`）；阶段 B：**IMPACT-CAST/BIBLE 已收口**（`0030` completed；发现 `0029`）；PUBLISH-02 仍 `proposed`；生产仍冻结
- 代码阶段：邮箱/GitHub 登录、资源隔离、Redis/ARQ、providers/tasks 分层、应用服务层、定妆锁定、多话壳、连载层、Playwright E2E、playground、生成归属收口、多人角色参考图、VPS nginx overlay、合集导出与摘要门禁已接入

## 当前事实

- 生成架构：`providers/` + `tasks/` 注册表；应用服务 `projects/assets/storyboard/generations/model_config/auth`；路由保持薄。
- 契约：任务状态无 `cancelled`；生成 SLA（job/stale/poll）由 Settings 统一；默认图像模型单源。
- 前端：TanStack Query 共享 `queryClient` 轮询生成任务；`lib/catalogs`；`useCurrentAccount`；Studio hydrate/autosave 抽出。
- Phase 1 工作区对齐：PNG + 制作资料 JSON 导出；检查器可编辑构图/剧情作用；侧栏多话切换与新建；角色 `reference_locked` 定妆锁定；作品库卡片与派生 `cover_image_url`。
- Phase 2 连载层：PRD 解冻 SERIAL-01..04 与 PROJ-04；作品设定集；伏笔 CRUD；AI 季策划与 from-plan 创建；话摘要与 continuity 注入分镜；作品总览 Tabs；独立阅读页。
- 路由：`/projects` 作品库；`/projects/new` 策划；`/projects/:id` 总览；`/projects/:id/studio` 工作区；`/projects/:id/read/:episodeId` 阅读；`/projects/:id/anthology-preview` 合集预览。
- API 资源名仍为 Project/Episode；产品文案为作品/话。迁移 head：`20261024_lettering_objects`。
- Playwright：`frontend/e2e` + Mailpit 登录；`make test-e2e` / `make test-e2e-ai`；E2E 用 `docker-compose.e2e.yml` + `--profile local`。
- Playground：`docker-compose.playground.yml`（独立卷/端口、fake-llm、Mailpit）；`make test-api-playground` / `test-e2e-playground` / `test-playground`。
- 部署：`docker-compose.prod.yml` + 共用机 `docker-compose.prod.nginx.yml`（禁 Caddy）；公网 `manxu.icatw.site`；私有运维脚本在 gitignored 的 `var/ops-private/`。生产图像已切 COS 并迁移校验 89 张；api/worker 正式镜像重建与密钥轮换仍待收口。
- 角色草稿：一次生成 2–6 人阵容并为每人出参考图（定妆锁定保留）。默认 `cast_mode=append`；`replace` 仅危险整队重建。
- 本话生成：已有作品角色库时默认 `regenerate_characters=false` 复用。
- 导出：本话「制作导出」长图/分页 ZIP/制作资料；成稿排版「导出成稿」PNG/ZIP/PDF（PUBLISH-01）；作品总览「导出合集」（ZIP/PDF，EXP-02）。
- 连载：第 N 话生成分镜前须有第 N-1 话非空摘要（409）。
- **产品方向**：面向个人连载漫画作者的静态图片创作工作台，竖条漫优先；路线、市场观察与阶段门槛见 `docs/product/roadmap-complete-comic.md`。
- **需求门禁**：`PAGE-01…03` / `LETTER-01…03` / `PUBLISH-01` 已确认、实现并手验（仓库内）；`COLLECT-PREVIEW-01` 已实现并手验（`0041`）；总览成稿入口抬升已收口（`0042`）；`PUBLISH-02` 仍 `proposed`；`INFRA-02` 已切流。

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
| SaaS 稳托（对象存储等） | 进行中 | 生产已切 COS（89 图已迁）；待正式镜像重建与密钥轮换；导出 blob / AUTH-07 仍待 |
| **静态漫画成稿层** | **A1–A3 完成；A′ 收口；B IMPACT 收口** | `0030` completed；PUBLISH-02 仍 proposed；生产仍冻结 |

## 下一步（tag 之后；默认不上线）

1. **阶段 B 余量**：DRAFT-RESUME 仍后置。勿开 PUBLISH-02；勿默认解冻生产。
2. **SaaS（0021）**：COS 正式镜像与密钥轮换可并行运维，不抢产品主线。
3. **模型测评（0031）**：脚手架已落；live 对照在 `var/model-eval/runs/`；再决定默认后端是否动。
4. **UIUX 余量**（未开 plan）：预览/导出命名收束；Studio「做完一话」轻引导；成稿清洁提示；可选 layout 就绪徽标。
