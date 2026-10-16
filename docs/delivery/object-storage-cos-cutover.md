# 腾讯云 COS 切流（INFRA-02 / ADR-004）

将生产图像从 Docker 卷 `image-data`（`IMAGE_STORAGE_DIR`）迁到 **私有** 腾讯云 COS。应用侧使用 S3 兼容客户端；读路径仍是鉴权后的 `GET /api/v1/assets/{id}` 代理流。

默认与 CI 保持 `OBJECT_STORE_BACKEND=local`。**未完成迁移校验前不要在生产强制 `s3`。**

---

## A. 控制台链接（先收藏）

| 用途 | 链接 |
| --- | --- |
| 腾讯云登录 | https://cloud.tencent.com/login |
| 控制台首页 | https://console.cloud.tencent.com |
| **对象存储 COS**（建桶） | https://console.cloud.tencent.com/cos |
| 存储桶列表（直达） | https://console.cloud.tencent.com/cos/bucket |
| **API 密钥**（SecretId / SecretKey） | https://console.cloud.tencent.com/cam/capi |
| 账号信息（查 APPID） | https://console.cloud.tencent.com/developer |
| 官方：控制台快速入门 | https://cloud.tencent.com/document/product/436/38484 |
| 官方：创建存储桶 | https://cloud.tencent.com/document/product/436/14106 |
| 官方：S3 兼容配置 | https://cloud.tencent.com/document/product/436/41284 |

漫序生产机在腾讯云广州一带时，**地域选「广州」= `ap-guangzhou`**（与下文示例一致）。若你确认 VPS 在别的地域，把下文所有 `ap-guangzhou` / `广州` 换成对应地域。

---

## B. 一步步：开通 COS + 建私有桶

### B1. 登录

1. 打开 https://cloud.tencent.com/login  
2. 用你跑 `manxu.icatw.site` / Studio 的**同一个腾讯云账号**登录。  
3. 若未实名：按控制台提示完成实名（COS 需要实名）。

### B2. 打开对象存储并开通

1. 打开（或收藏后点开）：https://console.cloud.tencent.com/cos  
2. 若第一次使用，页面会提示**开通对象存储 COS** → 按提示同意并开通。  
3. 开通后应能看到左侧菜单，例如「概览 / 存储桶列表 / …」。

> 也可在控制台顶部搜索框输入 **对象存储** 或 **COS**，点进产品页。

### B3. 创建存储桶（照着填）

1. 左侧点 **存储桶列表**，或直接打开：https://console.cloud.tencent.com/cos/bucket  
2. 点右上角（或列表上方）**创建存储桶**。  
3. 在表单里按下面填（其余保持默认即可）：

| 界面字段 | 建议填写 | 说明 |
| --- | --- | --- |
| **名称** | `manxu-assets` | 只能小写字母、数字、连字符；**创建后不能改**。系统会自动拼成 `名称-APPID`。 |
| **所属地域** | **广州** | 对应代码里的 `ap-guangzhou`。 |
| **访问权限** | **私有读写** | 必须私有；不要选「公有读」。 |
| 桶日志 / 版本控制 / 多 AZ 等 | 默认关闭即可 | 一期不需要。 |

4. 点 **创建** → 弹窗再确认 → **确定**。  
5. 回到存储桶列表，应能看到类似：

```text
manxu-assets-125xxxxxxxx
```

中间那一长串数字是你的 **APPID**。  
**完整桶名（含 `-APPID`）就是后面的 `S3_BUCKET`，请整段复制。**

### B4. 在桶里再确认一次「私有」

1. 点进刚建的桶名。  
2. 上方或左侧找 **权限管理** / **存储桶访问权限**（文案可能略有出入）。  
3. 确认是 **私有读写**。若不是，改成私有并保存。  
4. **不要**去开「静态网站」「默认公有读」「CDN 回源当默认读路径」之类；漫序图片走 API 鉴权代理，不需要公网直链。

### B5. 记下地域与 Endpoint（复制用）

建桶地域若是 **广州**，直接复制下面三行到记事本：

```env
S3_REGION=ap-guangzhou
S3_ENDPOINT=https://cos.ap-guangzhou.myqcloud.com
S3_ADDRESSING_STYLE=virtual
```

其他常见地域对照（选桶时看中文名即可）：

| 控制台地域 | `S3_REGION` | `S3_ENDPOINT` |
| --- | --- | --- |
| 广州 | `ap-guangzhou` | `https://cos.ap-guangzhou.myqcloud.com` |
| 上海 | `ap-shanghai` | `https://cos.ap-shanghai.myqcloud.com` |
| 北京 | `ap-beijing` | `https://cos.ap-beijing.myqcloud.com` |
| 成都 | `ap-chengdu` | `https://cos.ap-chengdu.myqcloud.com` |
| 重庆 | `ap-chongqing` | `https://cos.ap-chongqing.myqcloud.com` |

官方说明：https://cloud.tencent.com/document/product/436/41284  

---

## C. 一步步：拿 API 密钥（SecretId / SecretKey）

个人项目可先用**主账号密钥**（步骤少）。更稳妥是建「只读写该桶」的子用户；文末有可选加固。

### C1. 打开密钥页

1. 打开：https://console.cloud.tencent.com/cam/capi  
2. 若提示实名 / 二次验证，按页面完成。

### C2. 新建密钥

1. 点 **新建密钥**（或「创建密钥」）。  
2. 按提示完成手机/微信验证。  
3. 弹窗里会显示：
   - **SecretId**（一长串，可事后再查）  
   - **SecretKey**（**只在创建时完整显示一次**，立刻复制保存）  
4. 把两者粘到本地密码管理器或临时记事本（**不要提交到 git**）。

对应到漫序环境变量：

```env
S3_ACCESS_KEY_ID=<这里贴 SecretId>
S3_SECRET_ACCESS_KEY=<这里贴 SecretKey>
```

### C3. 拼好一整段 `.env.prod`（先别切流）

在服务器 `/opt/manxu-studio/.env.prod`（或本地将要 rsync 上去的文件）里，**追加或改成**类似下面（把尖括号换成你的值）。  
**此时仍保持 `OBJECT_STORE_BACKEND=local`。**

```env
# --- COS（先填密钥与桶；后端仍用本地卷）---
IMAGE_STORAGE_DIR=/app/var/images
OBJECT_STORE_BACKEND=local
S3_ENDPOINT=https://cos.ap-guangzhou.myqcloud.com
S3_REGION=ap-guangzhou
S3_BUCKET=manxu-assets-125xxxxxxxx
S3_ACCESS_KEY_ID=AKIDxxxxxxxx
S3_SECRET_ACCESS_KEY=xxxxxxxx
S3_ADDRESSING_STYLE=virtual
```

核对清单：

- [ ] `S3_BUCKET` = 列表里的**完整名**（含 `-APPID`），不是只写 `manxu-assets`  
- [ ] `S3_ENDPOINT` 地域与建桶地域一致  
- [ ] SecretKey 没多空格、没截断  
- [ ] `OBJECT_STORE_BACKEND` 仍是 `local`

---

## D. 迁移卷内文件 → COS（服务器命令，可复制）

### D1. 部署含迁移 CLI 的代码

在开发机同步后，到服务器：

```sh
cd /opt/manxu-studio
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  up -d --build --wait
```

### D2. dry-run（只列本地将要上传的文件，不访问桶）

```sh
cd /opt/manxu-studio
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  exec api \
  uv run python -m app.cli.migrate_images_to_s3 --dry-run
```

能看到若干行 `DRY  <uuid>.png ...` 或 `scanned=0`（没有历史图也正常）。

### D3. 实际上传并校验

```sh
cd /opt/manxu-studio
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  exec -e OBJECT_STORE_BACKEND=s3 api \
  uv run python -m app.cli.migrate_images_to_s3
```

期望末行类似：`failed=0`。脚本**不删除**卷里的文件。

可在 COS 控制台点进桶 → **文件列表**，应能看到 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.png` 这类对象。

若报签名 / 主机名错误：把 `.env.prod` 里 `S3_ADDRESSING_STYLE=virtual` 改成 `path`，保存后重跑 D3。

---

## E. 切流（确认迁移成功后再做）

1. 编辑 `.env.prod`，只改一行：

```env
OBJECT_STORE_BACKEND=s3
```

2. 重启 **api 与 worker**（都必须读同一套 env）：

```sh
cd /opt/manxu-studio
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.nginx.yml \
  --env-file .env.prod \
  up -d --build --wait
```

3. 浏览器冒烟：
   - 打开站点，登录  
   - 打开**已有**画格（刷新后图片仍在）  
   - **新生成**一张图 → 再刷新仍在  

---

## F. 回滚

1. `.env.prod` 改回：

```env
OBJECT_STORE_BACKEND=local
```

2. 再执行上面的 `up -d --build --wait`。  
3. 卷未删则可立刻回到切流前读路径。  
4. 切流后**新写入 COS** 的对象不会自动回到卷（本期脚本只做卷→桶）。

**不要**在验证通过前对 compose 使用 `down -v`。

---

## G. 子用户最小权限（推荐）

**不要把 SecretId / SecretKey 发到聊天、Issue 或 git。** 若已泄露：在子用户 API 密钥页禁用旧密钥并新建一对。

1. 打开 https://console.cloud.tencent.com/cam → **策略** → **新建自定义策略** → 按策略语法创建。  
2. 名称例如 `manxu-cos-assets-rw`，粘贴（当前桶 `manxu-assets-1255546834` / 广州）：

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "name/cos:PutObject",
        "name/cos:GetObject",
        "name/cos:HeadObject"
      ],
      "resource": [
        "qcs::cos:ap-guangzhou:uid/1255546834:manxu-assets-1255546834/*"
      ]
    },
    {
      "effect": "allow",
      "action": [
        "name/cos:GetBucket",
        "name/cos:HeadBucket"
      ],
      "resource": [
        "qcs::cos:ap-guangzhou:uid/1255546834:manxu-assets-1255546834"
      ]
    }
  ]
}
```

3. 给子用户（如 `manxu-cos`）关联该策略。  
4. 子用户详情 → **API 密钥** → 新建；只把密钥写进服务器 `/opt/manxu-studio/.env.prod`。  
5. 官方：https://cloud.tencent.com/document/product/436/11714  

---

## H. 后续（非本手册必做）

- 导出制作包仍在 Postgres `exports.content`；迁出对象存储见计划 `0021`。  
- 卷备份策略改为：COS 版本/生命周期 + 库备份；`image-data` 可在双写观察期后归档。
