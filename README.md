# 漫序 Studio

面向独立漫剧创作者和小型工作室的 AI 漫剧预制作工作台。

当前版本提供邮箱验证码注册登录、GitHub OAuth 登录、账户级模型配置和漫剧预制作工作区。项目、资产和异步生成任务按账户隔离。

## 技术栈

- 前端：React、TypeScript、Vite、React Router、TanStack Query、Tailwind CSS、shadcn/ui（源码组件按需求添加）。
- 后端：Python 3.13、FastAPI、Pydantic Settings、SQLAlchemy async、Alembic，使用 uv。
- 数据库：PostgreSQL。
- 接口：`docs/api/openapi.yaml` 是人工维护的契约源；前端类型由它生成。

## 本地启动

要求 Node.js 22.12+、pnpm 11.8+、uv、Docker Compose。

### 一键启动

Docker Desktop 启动后，在仓库根目录执行：

```sh
./scripts/start.sh
```

脚本会创建缺失的 `.env`、构建前端 Nginx、API 和 worker，并启动 PostgreSQL、Redis、Mailpit。停止服务：

```sh
./scripts/stop.sh
```

前端容器通过 Nginx 将 `/api` 代理到 API 容器，因此浏览器只需要访问 `http://localhost:5173`。Mailpit 使用 Compose profile `local`（`start.sh` 已带上）。

### 分进程开发（可选）

1. 复制 `.env.example` 为 `.env`。
2. 在 `.env` 配置 GitHub OAuth App 的 Client ID/Secret、回调地址，并设置至少 32 字符的 `MODEL_ENCRYPTION_KEY`（可用 `openssl rand -hex 32` 生成）。
3. 在仓库根目录运行 `docker compose --profile local up -d postgres redis mailpit`（PostgreSQL 映射到本机 55442，Redis 映射到 56379，Mailpit 网页位于 8025）。
4. 在 `backend/` 执行 `uv sync`，再从仓库根目录执行 `uv run --directory backend alembic upgrade head`。
5. 在 `frontend/` 执行 `pnpm install`。
6. 分别启动 API、ARQ worker 和前端：

   ```sh
   uv run --directory backend fastapi dev app/main.py
   uv run --directory backend arq app.worker.WorkerSettings
   pnpm --dir frontend dev
   ```

前端地址为 `http://localhost:5173`，API 文档为 `http://localhost:8000/docs`。Vite 将 `/api` 请求代理到本地 FastAPI。邮箱验证码通过本地 Mailpit 测试，收件箱为 `http://localhost:8025`。

## 生产部署（单机 VPS）

在已安装 Docker Compose v2.24+ 的 Linux 主机上：

```sh
cp .env.prod.example .env.prod
# 填写 DOMAIN、HTTPS 相关 URL、POSTGRES_PASSWORD、MODEL_ENCRYPTION_KEY、
# EMAIL_CODE_PEPPER、真实 SMTP（见文件内注释）
./scripts/deploy.sh
# 或 make deploy
```

Caddy 终止 TLS 并反代到前端；Postgres / Redis / API 不暴露公网。图像第一期仍使用命名卷 `image-data`。完整步骤、备份与远程同步见 [`docs/delivery/deploy-vps.md`](docs/delivery/deploy-vps.md)；决策见 [ADR-003](docs/technical/decisions/ADR-003-vps-compose-caddy.md)。

生产必须使用独立的 `EMAIL_CODE_PEPPER` 与真实 SMTP，并保持 `SESSION_COOKIE_SECURE=true`。GitHub OAuth 可选；模型 API Key 在登录后的设置页录入。

## 检查

- `make check`：OpenAPI lint、类型生成、前后端 lint/typecheck。
- `make test`：前后端自动化测试。
- `make migrate`：应用 Alembic 迁移。
- `make check-prod-env`：校验 `.env.prod` 生产门禁。

## 项目资料

- 产品和技术资料：[`docs/README.md`](docs/README.md)
- Harness 工作区、当前阶段和活动计划： [`.harness/README.md`](.harness/README.md)
- 接口契约流程：[`docs/api/README.md`](docs/api/README.md)
