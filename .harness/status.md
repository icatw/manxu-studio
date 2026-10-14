# 项目状态

- 更新时间：2026-10-15
- 当前阶段：多账户注册、资源隔离与 Redis 队列已实现；质量门禁和 Compose 基础验证通过
- 代码阶段：邮箱验证码/GitHub 登录、PostgreSQL 所有权、Redis/ARQ worker 已接入

## 当前事实

- 产品方向：面向独立创作者和小型工作室的 AI 漫剧预制作工作台。
- PRD：核心工作区首轮需求已确认；连载季策划、连续剧情线、章节摘要和阅读页 deferred。
- API：`docs/api/openapi.yaml` 已覆盖项目、故事单元、角色/场景、分镜、生成任务、图像版本和导出，并通过契约校验。
- API 响应：JSON 成功与错误统一为 `code/message/data/request_id`；请求日志带 request ID、耗时和稳定错误码，开发环境写入脱敏轮转 JSONL。
- 账户：邮箱验证码登录注册与 GitHub OAuth 多账户登录已接入；浏览器使用 HttpOnly Cookie/CSRF，后端接受 opaque Bearer session。身份与会话保存在 PostgreSQL；邮箱验证码使用 Redis TTL 与 HMAC pepper。
- 资源隔离：项目及故事、角色、场景、分镜、图片版本、任务和导出通过项目 owner 归属检查，跨账户返回 `404`；新增双账户 API 回归测试。
- 队列：生成任务先持久化到 PostgreSQL，再入 Redis/ARQ；worker 扫描未完成任务恢复调度，并用 PostgreSQL advisory lock 防止重复执行。
- 登录设置：登录页提供邮箱验证码、倒计时/重发/改邮箱与 GitHub 按钮；设置页展示账户登录身份。
- 本地运行：Compose 增加 Redis、Mailpit、API、worker 和图片持久卷。GitHub OAuth 仍需配置 Client ID/Secret；生产邮件需要 SMTP 与 `EMAIL_CODE_PEPPER`。
- 模型配置：文本端点、模型 ID 和密钥由账户设置保存；密钥使用 `MODEL_ENCRYPTION_KEY` 加密且接口不回显。当前环境尚未配置加密主密钥。
- 账户设置：`/settings` 集中展示 GitHub 头像、登录名、可编辑昵称及文本/Qwen Image 配置；设置入口位于工作区侧栏、项目库和窄屏工具栏。
- 本地 OAuth 排障：2026-10-14 callback 500 是数据库缺少 `accounts.display_name` 列；本地数据库现已升级到 `20261015_account_settings`（head）。再次登录需从 GitHub 登录入口获取新的 OAuth code。
- 图像地址：Qwen Image Base URL 可按账户编辑并持久化。此前的 `compatible-mode/v1` 地址来自百炼 Workspace 的 OpenAI 兼容 Base URL，最初用于文本请求；Qwen Image provider 会把 Workspace Host 映射为异步接口所需的 `/api/v1` 路径。
- 图像生成：Qwen Image 当前官方型号可选；任务经 DashScope 异步接口生成，图片落到 `IMAGE_STORAGE_DIR` 并经登录 API 提供。真实账户/API Key 调用尚未执行。
- 技术栈：采用 React/Vite + FastAPI；ADR-001 和 YAML-first ADR-002 已记录为 `accepted`。
- Harness：根目录 `AGENTS.md` 提供入口；`.harness/` 已收录工作流、状态和执行计划。产品/技术知识与 ADR 保持在 `docs/`。
- 工程仓库：Git 已初始化；前后端代码、依赖锁文件、迁移骨架和 CI 已建立。PostgreSQL 开发容器映射到本机 `55442`。

## 阶段与进度

| 阶段 | 状态 | 完成条件 |
| --- | --- | --- |
| 产品文档与初版 API 草案 | 完成 | 简报、PRD、流程、页面说明、领域模型、AI 管线和 YAML 草案已存在 |
| 需求确认与接口冻结 | 完成 | 首轮范围已确认；OpenAPI 补齐并冻结，类型由 YAML 生成 |
| 工程骨架 | 完成 | 前后端可启动、锁文件/迁移/CI/契约校验就绪 |
| 创作主流程演示切片 | 完成 | 项目 → 故事 → 角色/场景 → 分镜 → 图像版本 → 预览/PNG 导出已通过浏览器流程 |
| 服务端模型配置可见性 | 完成 | `.env` 配置项、无密钥配置摘要 API、OpenAPI 类型与工作区设置入口已接通 |
| 多账户注册与资源隔离 | 实现完成，待 GitHub OAuth 与双浏览器 E2E | 邮箱验证码、GitHub 登录、identity 表、owner 回填与跨账户 404 已实现 |
| Redis 与持久任务 worker | 基础验证完成，待任务恢复 E2E | Redis 限流/验证码、ARQ 调度、PostgreSQL 任务事实与恢复扫描已实现 |
| 自定义文本与 Qwen Image | 实现完成，待密钥验证 | OpenAI 兼容测试、Qwen 异步任务和图片持久化已实现 |
| 账户资料与模型设置页 | 实现完成，待登录浏览器验证 | 昵称更新、GitHub 头像展示、图像服务 Base URL 编辑和持久化已接入 |
| 统一 API 响应与日志 | 实现完成 | OpenAPI、FastAPI、前端客户端和回归测试已同步；生产由运行环境采集 stdout |
| 发布与交付 | 未开始 | 部署、演示录屏、运行说明和已知限制齐备 |

## 当前约束

邮箱验证码登录需要 Redis；开发 Compose 通过 Mailpit 投递。生产环境需配置 `EMAIL_CODE_PEPPER`、SMTP、GitHub OAuth Client ID/Secret 和 `MODEL_ENCRYPTION_KEY`。非浏览器客户端若需独立 Bearer token 签发/撤销，仍需后续增加专用 API token 表。

## 下一步

1. 配置 GitHub OAuth 凭据后完成浏览器 OAuth 和双账户隔离流程验证。
2. 使用真实生成任务验证失败重试和 worker 重启恢复。
3. 继续补齐团队制作需要的版本审阅与协同能力，但在范围确认前不引入团队权限系统。
