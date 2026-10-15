# 项目状态

- 更新时间：2026-10-15
- 当前阶段：生成架构重构（providers + task registry + story pipeline）在独立 worktree 完成并验证
- 代码阶段：邮箱验证码/GitHub 登录、PostgreSQL 所有权、Redis/ARQ worker 已接入；任务分发与供应商适配已分层

## 当前事实

- Worktree `kaiying-wt-arch-elegance` / 分支 `refactor/elegant-generation-architecture`：将巨石 `workspace_tasks` 拆为 `providers/` 与 `tasks/` 注册表；新增服务端 `story_pipeline`；前端一次提交故事起稿；ARQ pool 进程级复用。后端 46 测、前端 9 测与 typecheck 通过。
- API 客户端现已正确合并 `Request` 与 `RequestInit` 的 method/headers，修复项目创建缺少 JSON Content-Type、删除缺少 CSRF Header 的问题；客户端回归测试与前端质量门禁通过。
- Workspace API 已拆分为项目/故事、角色/场景、分镜和生成/导出四组路由；共享鉴权依赖与任务构造集中在 `workspace_common.py`。
- 产品方向：面向独立创作者和小型工作室的 AI 漫剧预制作工作台。
- PRD：核心工作区首轮需求已确认；连载季策划、连续剧情线、章节摘要和阅读页 deferred。
- API：`docs/api/openapi.yaml` 已覆盖项目、故事单元、角色/场景、分镜、生成任务、图像版本和导出，并通过契约校验。
- API 响应：JSON 成功与错误统一为 `code/message/data/request_id`；请求日志带 request ID、耗时和稳定错误码，开发环境写入脱敏轮转 JSONL。
- 账户：邮箱验证码登录注册与 GitHub OAuth 多账户登录已接入；浏览器使用 HttpOnly Cookie/CSRF，后端接受 opaque Bearer session。身份与会话保存在 PostgreSQL；邮箱验证码使用 Redis TTL 与 HMAC pepper。
- 资源隔离：项目及故事、角色、场景、分镜、图片版本、任务和导出通过项目 owner 归属检查，跨账户返回 `404`；新增双账户 API 回归测试。
- 队列：生成任务先持久化到 PostgreSQL，再入 Redis/ARQ；worker 扫描未完成任务恢复调度，并用 PostgreSQL advisory lock 防止重复执行。
- 登录设置：登录页提供邮箱验证码、倒计时/重发/改邮箱与 GitHub 按钮；设置页展示账户登录身份。
- 身份验证语义：GitHub OAuth 身份以成功 OAuth 登录作为已验证；邮箱身份仍以验证码验证时间为准。回归测试覆盖两类身份。
- 本轮浏览器验收：GitHub 登录方式只显示一条“已验证”；项目创建请求返回 `201`、带 JSON 与 CSRF 请求头；工作区故事编辑显示已保存，刷新后项目仍存在；确认删除后临时项目从列表消失，数据库只读计数为 0。未修改或删除原有项目。
- 浏览器自动化发现：原生 `window.confirm` 会让当前 Chrome 自动化会话在系统锁屏时失去响应；项目删除已改用应用内可访问确认框，并在独立本地浏览器标签中完成验证。
- 启动镜像修复：运行时设置 `UV_NO_DEV=1`，避免 `uv run` 在无网络时重新安装开发依赖；此前 Compose API 因下载 pytest 超时未能启动，修复后 API 与前端均 healthy。
- 模型工作台：当前账户已配置文本模型 `qwen3.8-flash` 与图像模型 `qwen-image-3.0-pro`；密钥留在服务端加密存储。本地开发使用忽略的 `.env` 中的 `MODEL_ENCRYPTION_KEY`，生产部署仍需自行注入并持久保管。
- 本地运行：Compose 增加 Redis、Mailpit、API、worker 和图片持久卷。GitHub OAuth 仍需配置 Client ID/Secret；生产邮件需要 SMTP 与 `EMAIL_CODE_PEPPER`。
- 模型配置：文本端点、模型 ID 和密钥由账户设置保存；密钥使用 `MODEL_ENCRYPTION_KEY` 加密且接口不回显。本地 Compose 已配置开发主密钥；替换或丢失主密钥会导致已保存模型密钥无法解密。
- 账户设置：`/settings` 集中展示 GitHub 头像、登录名、可编辑昵称及文本/Qwen Image 配置；设置入口位于工作区侧栏、项目库和窄屏工具栏。
- 本地 OAuth 排障：2026-10-14 callback 500 是数据库缺少 `accounts.display_name` 列；本地数据库现已升级到 `20261015_account_settings`（head）。再次登录需从 GitHub 登录入口获取新的 OAuth code。
- 图像地址：Qwen Image Base URL 可按账户编辑并持久化。此前的 `compatible-mode/v1` 地址来自百炼 Workspace 的 OpenAI 兼容 Base URL，最初用于文本请求；Qwen Image provider 会把 Workspace Host 映射为异步接口所需的 `/api/v1` 路径。
- 图像生成：Qwen Image 任务经 DashScope 异步接口生成，图片落到 `IMAGE_STORAGE_DIR` 并经登录 API 提供。2026-10-15 已用当前账户真实调用文本模型与 Qwen Image：角色、3 个场景、4 格分镜全部生成并持久化；角色图可在浏览器加载。角色来源写入 `generation_source=ai`，前端明确显示“AI 起稿”。
- AI 生成回归：修复场景生成将 `name` 重复写入 profile 导致工作区 `GET scenes` 500；写入时排除名称字段，读取时兼容清理历史 JSON 中的重复字段。后端回归测试与浏览器刷新验证通过。
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
| 自定义文本与 Qwen Image | 真实账户端到端验证完成 | 文本模型生成角色/场景/分镜，Qwen Image 生成持久角色参考图，并通过浏览器刷新验证 |
| 账户资料与模型设置页 | 完成基础浏览器验证 | 昵称更新、GitHub 头像展示、图像服务 Base URL 编辑和持久化已接入 |
| 统一 API 响应与日志 | 实现完成 | OpenAPI、FastAPI、前端客户端和回归测试已同步；生产由运行环境采集 stdout |
| 发布与交付 | 未开始 | 部署、演示录屏、运行说明和已知限制齐备 |

## 当前约束

邮箱验证码登录需要 Redis；开发 Compose 通过 Mailpit 投递。生产环境需配置 `EMAIL_CODE_PEPPER`、SMTP、GitHub OAuth Client ID/Secret 和 `MODEL_ENCRYPTION_KEY`。非浏览器客户端若需独立 Bearer token 签发/撤销，仍需后续增加专用 API token 表。

## 下一步

1. 配置 GitHub OAuth 凭据后完成浏览器 OAuth 和双账户隔离流程验证。
2. 验证真实生成失败重试和 worker 重启恢复。
3. 继续补齐团队制作需要的版本审阅与协同能力，但在范围确认前不引入团队权限系统。
