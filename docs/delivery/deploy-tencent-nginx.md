# 腾讯云共用机部署（nginx 边缘，保留现有站点）

适用：`ssh tencent` 这台机已用 **主机 nginx** 占 80/443，并跑着 blog / Hermes 等。  
目标：上线漫序 Studio，**不抢端口、不改其它站点配置、不删现有 Docker 卷**。

默认 `docker-compose.prod.yml` 里的 Caddy 会绑 80/443，**这台机不要用**。改用：

```text
docker-compose.yml
+ docker-compose.prod.yml
+ docker-compose.prod.nginx.yml   # 禁用 Caddy；frontend → 127.0.0.1:13080
+ 主机 nginx 新 vhost（acme.sh 证书）
```

## 保留现有数据的原则

1. **只新增**：新目录（建议 `/opt/manxu-studio`）、新 compose project、新 nginx site、新子域名。  
2. **不要**：停主机 nginx、改其它 `sites-enabled`、对无关容器 `docker compose down -v`、全盘 `docker system prune -a --volumes`。  
3. 漫序自己的 Postgres / 图片在 **本 compose 的命名卷**（`postgres-data`、`image-data`）。以后更新用 `up -d --build`，**不要加 `-v`**，数据会留下。  
4. 本机第一次部署没有漫序业务数据可迁；若本地有要带上去的库，另做卷备份导入（见文末）。

## 前置

- [ ] 磁盘有余量（建议 ≥10G）；可先 `docker builder prune`（只清 build cache，不动卷）  
- [ ] DNS：`studio.icatw.site`（或自定）A 记录 → `124.222.146.241`  
- [ ] 真实 SMTP（生产不用 Mailpit）  
- [ ] 本机或服务器上准备好 `.env.prod`（勿提交 git）

## 步骤

### 1. 同步代码

在开发机：

```sh
./scripts/deploy-remote.sh tencent /opt/manxu-studio
```

注意：当前 `deploy-remote.sh` 末尾会跑默认 `deploy.sh`（含 Caddy）。**第一次在共用机上**建议先只 rsync，再手工 compose：

```sh
rsync -az --delete \
  --exclude '.git' --exclude 'node_modules' --exclude '.venv' \
  --exclude 'frontend/node_modules' --exclude 'frontend/dist' \
  --exclude 'var' --exclude 'backend/.data' \
  --exclude '.env' --exclude '.env.prod' \
  ./ tencent:/opt/manxu-studio/

# 若本地有 .env.prod，单独拷贝（会覆盖远端同名文件）
rsync -az .env.prod tencent:/opt/manxu-studio/.env.prod
```

### 2. 填写 `.env.prod`

在服务器 `/opt/manxu-studio/.env.prod`（可由 `.env.prod.example` 复制）：

```env
DOMAIN=studio.icatw.site
CORS_ORIGINS=https://studio.icatw.site
FRONTEND_BASE_URL=https://studio.icatw.site
GITHUB_CALLBACK_URL=https://studio.icatw.site/api/v1/auth/github/callback
SESSION_COOKIE_SECURE=true
FRONTEND_HOST_PORT=13080
# POSTGRES_PASSWORD / MODEL_ENCRYPTION_KEY / EMAIL_CODE_PEPPER / SMTP_* 必填
```

密钥变更会使已存模型 API Key 无法解密，生产上要固定保存。

### 3. 启动应用栈（无 Caddy）

```sh
ssh tencent
cd /opt/manxu-studio
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  up -d --build --wait
```

确认：`curl -sS http://127.0.0.1:13080/` 有前端；`docker compose … ps` 里 **没有** 抢 80/443 的 caddy。

### 4. 证书 + nginx site

与现有站点一样用 acme.sh（示例）：

```sh
# 按你机器上的 acme.sh 习惯签发 studio.icatw.site
sudo cp deploy/nginx-manxu-icatw.site.conf.example /etc/nginx/sites-available/studio-icatw
# 编辑证书路径与 server_name
sudo ln -sf /etc/nginx/sites-available/studio-icatw /etc/nginx/sites-enabled/studio-icatw
sudo nginx -t && sudo systemctl reload nginx
```

### 5. 冒烟

- `https://studio.icatw.site/api/v1/health`  
- 邮箱登录 / 建作品 / 出图（设置页填模型 Key）  
- 图片刷新后仍在（`image-data` 卷）

对象存储（INFRA-02 / ADR-004）：默认仍用卷上的 `IMAGE_STORAGE_DIR`。切腾讯云 COS 的建桶、迁移 CLI、切流与回滚见 [object-storage-cos-cutover.md](object-storage-cos-cutover.md)。

## 更新（保留漫序数据）

```sh
# 同步代码后：
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  up -d --build --wait
```

**禁止**对漫序 project 使用 `down -v`，除非你明确要清空库和图片。

### 构建为什么慢 / 怎么加速

国内 VPS 直连 `ghcr.io`、PyPI、npm 常极慢或超时（本次正式重建失败点：`uv` 镜像与 `asyncpg` wheel）。

已做的镜像内优化：

- backend：不再 `FROM ghcr.io/astral-sh/uv`，改用清华 PyPI 装 `uv`，`UV_HTTP_TIMEOUT=120`
- frontend：`registry.npmmirror.com`

仍慢时的运维手段：

1. **本机构建再导入**（最稳）：Mac 上 `docker compose build`，`docker save … | gzip | ssh tencent docker load`，服务器只 `up -d --no-build`。
2. **Build 走主机代理**：若主机 Mihomo 在 `7890`，构建时加  
   `docker compose build --build-arg HTTP_PROXY=http://172.17.0.1:7890 --build-arg HTTPS_PROXY=…`（并保证防火墙放行）。  
   注意：compose `up --build` 默认**不会**把运行时 `.env.prod` 的 `HTTP_PROXY` 传给 `RUN` 层。
3. **Docker Hub 镜像加速**：在 `/etc/docker/daemon.json` 配置腾讯云/DaoCloud registry-mirrors（只加速 Hub，不加速 ghcr）。
4. 磁盘 >85% 时先 `docker builder prune`（勿对漫序 `down -v`）。

## 可选：从本机迁入演示数据

仅当要把本地 Postgres / 图片带到服务器时：

1. 本机 `docker compose stop` 后打包卷  
2. 传到服务器后恢复到**同名** compose 卷  
3. 再 `up -d`  

日常演示账号在线上重新登录配置即可，多数情况不必迁库。
