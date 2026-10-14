# 漫序 Studio

面向独立漫剧创作者和小型工作室的 AI 漫剧预制作工作台。

当前仓库阶段是工程骨架。产品需求和接口仍在确认中；除系统 health/version 外，不实现尚未确认的产品操作。

## 技术栈

- 前端：React、TypeScript、Vite、React Router、TanStack Query、Tailwind CSS、shadcn/ui（源码组件按需求添加）。
- 后端：Python 3.13、FastAPI、Pydantic Settings、SQLAlchemy async、Alembic，使用 uv。
- 数据库：PostgreSQL。
- 接口：`docs/api/openapi.yaml` 是人工维护的契约源；前端类型由它生成。

## 本地启动

要求 Node.js 22.12+、pnpm 11.8+、uv、Docker Compose。

1. 复制 `.env.example` 为 `.env`。
2. 在仓库根目录运行 `docker compose up -d postgres`（映射到本机 55442 端口，避免占用其他本地数据库端口）。
3. 在 `backend/` 执行 `uv sync`，再从仓库根目录执行 `uv run --directory backend alembic upgrade head`。
4. 在 `frontend/` 执行 `pnpm install`。
5. 分别启动 API 和前端：

   ```sh
   uv run --directory backend fastapi dev app/main.py
   pnpm --dir frontend dev
   ```

前端地址为 `http://localhost:5173`，API 文档为 `http://localhost:8000/docs`。Vite 将 `/api` 请求代理到本地 FastAPI。

## 检查

- `make check`：OpenAPI lint、类型生成、前后端 lint/typecheck。
- `make test`：前后端自动化测试。
- `make migrate`：应用 Alembic 迁移。

## 项目资料

- 产品和技术资料：[`docs/README.md`](docs/README.md)
- Harness 工作区、当前阶段和活动计划： [`.harness/README.md`](.harness/README.md)
- 接口契约流程：[`docs/api/README.md`](docs/api/README.md)
