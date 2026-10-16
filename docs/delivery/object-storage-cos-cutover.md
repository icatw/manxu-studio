# 腾讯云 COS 切流（INFRA-02 / ADR-004）

将生产图像从 Docker 卷 `image-data`（`IMAGE_STORAGE_DIR`）迁到 **私有** 腾讯云 COS。应用侧使用 S3 兼容客户端；读路径仍是鉴权后的 `GET /api/v1/assets/{id}` 代理流。

默认与 CI 保持 `OBJECT_STORE_BACKEND=local`。**未完成迁移校验前不要在生产强制 `s3`。**

## 1. 建桶与密钥（控制台）

1. 地域与 VPS 尽量同区（例如 `ap-guangzhou`）。
2. 创建私有桶；关闭公有读；不配 CDN 作为默认读路径。
3. 创建仅该桶读写权限的 API 密钥（或子账号），记下：
   - `S3_BUCKET`（含 AppId 后缀时按控制台完整桶名）
   - `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`
4. Endpoint 示例：`https://cos.ap-guangzhou.myqcloud.com`  
   `S3_REGION=ap-guangzhou`，`S3_ADDRESSING_STYLE=virtual`（若 SDK 报签名/主机错误再试 `path`）。

把上述变量写入服务器 `.env.prod`（**先不要**改 `OBJECT_STORE_BACKEND`，仍保持 `local`）。

## 2. 部署含迁移 CLI 的镜像

同步代码并重建 api/worker（仍用 local 后端）：

```sh
cd /opt/manxu-studio
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  up -d --build --wait
```

## 3. 迁移卷内文件 → COS

在 **api 容器** 内执行（挂载了 `image-data` → `/app/var/images`）。迁移命令会读完整 `S3_*`，因此临时把后端设为 s3 **仅用于本命令进程**，或先在 `.env.prod` 填好 `S3_*` 后用环境覆盖：

```sh
# dry-run：只列将上传的 {uuid}.png|jpg|webp（不访问桶）
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  exec api \
  uv run python -m app.cli.migrate_images_to_s3 --dry-run

# 实际上传并逐文件字节校验；已存在且 ContentLength 一致则跳过
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  exec -e OBJECT_STORE_BACKEND=s3 api \
  uv run python -m app.cli.migrate_images_to_s3
```

期望输出末行 `failed=0`。脚本 **不删除** 卷内文件。

本地开发等价：

```sh
OBJECT_STORE_BACKEND=s3 S3_ENDPOINT=... S3_BUCKET=... \
  S3_ACCESS_KEY_ID=... S3_SECRET_ACCESS_KEY=... \
  uv run --directory backend python -m app.cli.migrate_images_to_s3 --dry-run
```

## 4. 切流

1. `.env.prod` 设 `OBJECT_STORE_BACKEND=s3`（`S3_*` 已齐）。
2. 重建/重启 **api 与 worker**（二者都必须能读同一桶）：

```sh
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  up -d --build --wait
```

3. 冒烟：登录 → 打开已有画格（刷新后仍可见）→ 新生成一张图 → 再刷新。

## 5. 回滚

1. `.env.prod` 改回 `OBJECT_STORE_BACKEND=local`。
2. 重启 api/worker。卷未删则可立刻回到切流前读路径。
3. 切流后新写入 COS 的对象不会自动回到卷；若需保留，再跑一次「从 COS 拉回」需另做（本期脚本只做卷→桶）。

**不要**在验证通过前对 compose 使用 `down -v`。

## 6. 后续（非本手册必做）

- 导出制作包仍在 Postgres `exports.content`；迁出对象存储见计划 `0021`。
- 卷备份策略改为：COS 版本/生命周期 + 库备份；`image-data` 可在双写观察期后归档。
