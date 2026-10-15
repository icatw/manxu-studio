# 单机 VPS 部署（Compose + Caddy）

第一期目标：在一台已安装 Docker Compose v2.24+ 的 Linux VPS 上，用现有应用镜像栈对外提供 HTTPS。图像文件仍写在 Docker 命名卷 `image-data`（api 与 worker 共享）；对象存储、托管数据库与 CI 自动发布不在本范围。

## 架构

浏览器 → Caddy（80/443，自动 ACME）→ frontend Nginx（静态 + `/api` 反代）→ api；worker 消费 Redis 队列；Postgres / Redis / API 不映射到公网。

本地开发继续用 `./scripts/start.sh`（`--profile local`，含 Mailpit），与生产 overlay 分开。

## 前置条件

1. VPS 已安装 Docker Engine 与 Compose v2.24+（支持 `!reset` / `!override`）。
2. 域名 A/AAAA 指向该机；防火墙放行 80/443。
3. 可用的真实 SMTP（生产禁用 Mailpit）。
4. 仓库已克隆到 VPS（或本机用 `./scripts/deploy-remote.sh` 同步）。

## 首次部署

```sh
cp .env.prod.example .env.prod
# 编辑 .env.prod：DOMAIN、CORS/FRONTEND URL、POSTGRES_PASSWORD、
# MODEL_ENCRYPTION_KEY、EMAIL_CODE_PEPPER、SMTP_*
openssl rand -hex 32   # 用于 MODEL_ENCRYPTION_KEY 与 EMAIL_CODE_PEPPER（各生成一次）

./scripts/check-prod-env.sh
./scripts/deploy.sh
# 或：make deploy
```

浏览器打开 `https://$DOMAIN`。健康检查：`https://$DOMAIN/api/v1/health`。

可选从开发机推送：

```sh
./scripts/deploy-remote.sh user@vps /opt/manxu-studio
# 或：make deploy-remote REMOTE=user@vps REMOTE_PATH=/opt/manxu-studio
```

远端必须已有 Docker；脚本会 rsync 代码（默认不同步 `.git`），若本地有 `.env.prod` 会覆盖远端同名文件，然后执行 `deploy.sh`。

## 更新

在 VPS 仓库目录：

```sh
git pull   # 或再次 deploy-remote
./scripts/deploy.sh
```

API 容器启动时仍会执行 `alembic upgrade head`。worker 无独立 healthcheck；用 `docker compose … ps` 与生成任务确认其存活。

## 备份（第一期）

至少备份命名卷：

- `postgres-data`：账户与业务数据
- `image-data`：生成图片；丢失则资产 URL 失效
- `caddy-data`：TLS 证书（可重建，但备份可避免频繁申请）

示例（停止写入窗口后）：

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod stop
docker run --rm -v kaiying_postgres-data:/data -v "$(pwd)/backup:/backup" alpine \
  tar czf /backup/postgres-data.tgz -C /data .
docker run --rm -v kaiying_image-data:/data -v "$(pwd)/backup:/backup" alpine \
  tar czf /backup/image-data.tgz -C /data .
```

项目名（卷前缀）以 `docker compose … config --volumes` / `docker volume ls` 为准。

## 密钥与安全

- `.env.prod` 已 gitignore；勿提交。
- `MODEL_ENCRYPTION_KEY` 变更会使已加密的模型 API Key 无法解密。
- `SESSION_COOKIE_SECURE=true` 与 HTTPS 必须同时满足。
- 不要设置 `ALLOW_PRIVATE_MODEL_BASE_URLS=true`。
- 生产不自动 seed 演示数据。

## 明确不做

对象存储（S3）、托管 Postgres、多机编排、镜像仓库 CI 推送、独立 worker 健康探针（后续）。
