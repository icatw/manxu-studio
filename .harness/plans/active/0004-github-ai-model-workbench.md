# GitHub 登录与 AI 模型工作台

## 目标

交付首个账户与真实模型切片：GitHub 首账户锁定登录、账户级文本模型配置、连通性测试和 Qwen Image 异步任务。OpenAPI YAML 是接口源，先于实现更新。

## 约束与决策

- 首位 GitHub 登录成功的账户成为唯一用户；后续只允许该 GitHub 身份登录。
- 登录成功时，将项目和关联记录中的未归属存量记录归给该账户。
- 文本 Base URL 仅允许公网 HTTPS；请求前及 DNS 解析后阻止回环、私网、链路本地和云元数据地址。
- OAuth 与模型密钥仅存服务端；模型密钥加密保存。会话使用 HttpOnly、SameSite Cookie。
- Qwen Image 结果保存服务端持久目录，外部下载 URL 不直接发给浏览器。
- 当前认证作用于个人单账户部署，不做组织/团队权限。

## 执行状态

- [x] 更新 PRD 需求与 OpenAPI 契约。
- [x] 建立本计划并按 YAML 生成客户端类型。
- [x] 添加账户、会话、模型配置数据模型与 Alembic 迁移。
- [x] 实现 OAuth、会话校验、配置加密/解密、连接测试与端点网络限制。
- [x] 接入 Qwen Image 异步生成并持久保存图片。
- [x] 接入登录门禁、配置 UI 和图像任务前端。
- [x] 增加 API/provider/UI 测试并运行 lint/typecheck/build。
- [x] 更新状态文档；实现交付完成，保留本计划供凭据配置后的外部联调。

## 验收证据

- `pnpm api:lint`, `pnpm api:types`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` 通过；lint 有 3 条既有 Fast Refresh 警告，build 有 bundle 体积提示。
- 后端 Ruff、mypy 和 pytest 通过（12 项）；Alembic 已升级到 `20261014_account_workbench`。
- Playwright 确认未登录页面、登录按钮和 OAuth 配置缺失提示；真实 OAuth 和模型调用未验证，当前环境缺 OAuth 凭据和加密主密钥。

## 决策日志

- 初始 Git 提交：`a79cc19` (`chore: initialize Manxu Studio project`)，本地运行产物保持未跟踪且由 `.gitignore` 排除。
- 当前 OpenAPI 已更新并重新生成 TypeScript 类型；契约包含账户、模型设置、连接测试和私有图片资源。
