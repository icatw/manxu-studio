# 漫序 Studio

面向独立漫剧创作者和小型工作室的 AI 漫剧预制作工作台。

当前版本提供 GitHub 单账户登录、模型配置和漫剧预制作工作区。首个完成 OAuth 登录的 GitHub 账户会成为唯一账户。

## 技术栈

- 前端：React、TypeScript、Vite、React Router、TanStack Query、Tailwind CSS、shadcn/ui（源码组件按需求添加）。
- 后端：Python 3.13、FastAPI、Pydantic Settings、SQLAlchemy async、Alembic，使用 uv。
- 数据库：PostgreSQL。
- 接口：`docs/api/openapi.yaml` 是人工维护的契约源；前端类型由它生成。

## 本地启动

要求 Node.js 22.12+、pnpm 11.8+、uv、Docker Compose。

1. 复制 `.env.example` 为 `.env`。
2. 在 `.env` 配置 GitHub OAuth App 的 Client ID/Secret、回调地址，并设置至少 32 字符的 `MODEL_ENCRYPTION_KEY`（可用 `openssl rand -hex 32` 生成）。
3. 在仓库根目录运行 `docker compose up -d postgres`（映射到本机 55442 端口）。
4. 在 `backend/` 执行 `uv sync`，再从仓库根目录执行 `uv run --directory backend alembic upgrade head`。
5. 在 `frontend/` 执行 `pnpm install`。
6. 分别启动 API 和前端：

   ```sh
   uv run --directory backend fastapi dev app/main.py
   pnpm --dir frontend dev
   ```

前端地址为 `http://localhost:5173`，API 文档为 `http://localhost:8000/docs`。Vite 将 `/api` 请求代理到本地 FastAPI。

在 GitHub OAuth App 中将 Authorization callback URL 设置为 `GITHUB_CALLBACK_URL`。文本模型和 Qwen Image 的 API Key 在登录后的模型设置中录入；Qwen Image 区域 endpoint 通过 `QWEN_IMAGE_BASE_URL` 设置，图片文件保存于 `IMAGE_STORAGE_DIR`，部署时需将其挂载到持久卷。生产环境必须启用 `SESSION_COOKIE_SECURE=true` 并通过 HTTPS 访问。

## 检查

- `make check`：OpenAPI lint、类型生成、前后端 lint/typecheck。
- `make test`：前后端自动化测试。
- `make migrate`：应用 Alembic 迁移。

## 项目资料

- 产品和技术资料：[`docs/README.md`](docs/README.md)
- Harness 工作区、当前阶段和活动计划： [`.harness/README.md`](.harness/README.md)
- 接口契约流程：[`docs/api/README.md`](docs/api/README.md)
