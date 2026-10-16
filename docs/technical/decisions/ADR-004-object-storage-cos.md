# ADR-004：对象存储采用腾讯云 COS（S3 兼容接入）

- 状态：accepted
- 日期：2026-10-16
- 关联需求：INFRA-02（`confirmed`；生产强制切 S3/COS 前须完成桶与迁移验证）

## 背景

[ADR-003](ADR-003-vps-compose-caddy.md) 第一期将图像放在 Docker 命名卷 `image-data`。SaaS 稳托阶段需要：多实例可共享、可备份、磁盘与应用解耦。架构已预留 `ObjectStore` 协议与 `LocalObjectStore`；待决的是生产供应商。

生产实例跑在腾讯云 VPS（`manxu.icatw.site`），图像为账户私有资产，须鉴权后访问。

## 候选

1. **腾讯云 COS**（同云、S3 兼容 API）
2. **阿里云 OSS**（S3 兼容较好，需另开阿里账号）
3. **Cloudflare R2**（S3 兼容、出口友好；国内到 R2 链路一般）
4. **AWS S3**（标准；国内延迟与账号成本不利）
5. **自建 MinIO**（开发便利；耐久与备份仍在单机上）

## 决定

采用候选 1：**腾讯云 COS**，应用侧只实现 **S3 兼容客户端**（可配置 `endpoint` / `region` / `bucket` / AK·SK），不绑定 COS 专有 SDK 为唯一路径。

本地与 CI 继续可用 `LocalObjectStore`（或可选 MinIO）；生产默认 COS。

## 理由

- 与现有腾讯云 VPS / 账号体系一致；同地域可用内网访问，降低延迟与外网流量成本。
- COS 对常用 S3 操作（Put/Get、预签名、multipart）足够支撑当前读写模型。
- S3 兼容适配器便于日后切到 OSS/R2，而不改业务服务边界。
- R2/S3 更适合出海或全球分发，不是当前国内私有创作资产的第一站。
- MinIO 不解决「离开单机卷」的耐久与运维目标。

## 后果

- 新增环境变量（示例名）：`OBJECT_STORE_BACKEND=local|s3`、`S3_ENDPOINT`、`S3_REGION`、`S3_BUCKET`、`S3_ACCESS_KEY_ID`、`S3_SECRET_ACCESS_KEY`（及可选 path-style / 内网 endpoint）。
- 数据库存 object key 与元数据；下载路径：校验账户所有权后 **短时预签名 URL** 或继续经 API 代理流（产品确认时二选一或并存）。
- 桶保持 **私有**；一期不做公网 CDN 直出未鉴权图片。
- 需一次性迁移脚本：卷内已有文件 → COS，并回填元数据。
- 备份策略从「备份 `image-data` 卷」扩展为「COS 版本/跨区域策略 + 库备份」。
- INFRA-02 在 PRD 确认为 `confirmed` 并更新 OpenAPI 前，不得合并生产强制切 COS 的破坏性变更。

## 非目标（本期）

- 多云双写、跨厂商灾备自动化。
- 公开桶 + CDN 作为默认读路径。
- 用对象存储替代 PostgreSQL 中的业务事实。
