# ADR-003：单机 VPS 采用 Compose + Caddy 部署

- 状态：accepted
- 日期：2026-10-15

## 背景

本地已有 `docker compose` 一键栈与 Nginx 前端反代，但缺少生产 HTTPS、公网端口收敛、真实 SMTP 与部署脚本。架构文档将部署平台与对象存储标为待决；交付阶段需要先能稳定上线演示/单租户实例。

## 候选

1. 单机 VPS + 现有 Compose + Caddy 自动 HTTPS  
2. PaaS（Fly / Render / Railway）拆服务 + 托管 Postgres  
3. Kubernetes / 托管容器服务  

## 决定

采用候选 1。第一期图像继续使用 api/worker 共享的 Docker 命名卷 `image-data`，不引入对象存储。

## 理由

- 与现有 Dockerfile / Compose / Alembic-on-boot / ARQ worker 一致，改动面最小。  
- Caddy 提供 ACME 证书，比自管 certbot + 第二层 Nginx 脚本更简单。  
- 单机演示与早期生产足够；S3 与托管库可在 SaaS 化时替换卷与 Postgres 服务而不推翻应用边界。

## 后果

- 运维需自行备份 `postgres-data` 与 `image-data`。  
- 水平扩展与多区域不在第一期范围。  
- 生产使用 `docker-compose.prod.yml` overlay；本地 `start.sh` 使用 `--profile local`（Mailpit），二者不得混用。
