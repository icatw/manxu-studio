# SaaS 准备清单（现状对齐）

> 更新：2026-10-17。对照里程碑 `v0.1.0-storyboard` 与当前仓库实现。  
> **生产部署**：该 tag 之后默认冻结向 `manxu.icatw.site` 推送应用更新，见 `.harness/status.md`。

## 结论

多账户隔离、邮箱/GitHub 登录、Redis/ARQ 任务、账户级模型配置、图像对象存储（COS）已落地，足以支撑**邀请制**试用。  
**仍不得开放自助注册/收费**，直到身份恢复（AUTH-07）、生产邮件可信送达、用量与失败重试可追踪、备份/删除说明齐备。

## 已完成（相对旧稿）

| 主题 | 状态 | 说明 |
| --- | --- | --- |
| 账户与会话 | 完成 | 邮箱验证码 + GitHub OAuth；HttpOnly Cookie + CSRF；Bearer 会话边界见契约 |
| 资源所有权 | 完成 | `current_account` + 项目/子资源归属；跨账户统一 404；双账户测试存在 |
| 模型 BYOK | 完成 | 账户级文本/图像配置，Key 加密存储、不回显 |
| 异步任务 | 完成 | Redis + ARQ worker；任务归属与恢复路径已接入（非 FastAPI BackgroundTasks 主路径） |
| 图像存储 INFRA-02 | 完成（生产已切流） | `ObjectStore` local\|s3；腾讯 COS；鉴权后 API 代理读；里程碑已迁 89 张图 |
| 连载创作主路径 | 完成 | 作品/话、设定、分镜、画格、EXP 制作导出（见 PRD `confirmed`） |

旧版本文档中的「登录仍锁首账户 / `account_registry` 当所有者 / 未做所有权校验」**已过时**，勿再当作开放注册阻断项的现状描述。

## 仍缺口（开放注册或收费前置）

### 不挡「邀请制、用线上 tag 能力试用」

- COS 密钥轮换（聊天曾泄露则必做）；正式 api/worker 镜像重建（可用本机构建导入，**当前冻结生产应用更新**）。
- 文档/口径：试用只承诺分镜与画格 + 制作预览导出，不成稿 PAGE/LETTER。

### 挡「开放自助注册」

- **AUTH-07**：设置页主动绑定邮箱/第三方；禁止仅凭同邮箱静默合并。
- 生产邮件：专用发信域 + SPF/DKIM/DMARC；开发用 Mailpit；验证送达率。
- 账户数据导出与删除（含项目、密钥、任务、图片、导出）的保留策略与操作路径。
- 隐私政策 / 服务条款（登录数据、模型调用、存储）。

### 挡「平台代付或公开收费」

- 文本/图像操作的估算与实际消耗账本；失败/重试计费规则可读。  
  **进度**：实际消耗账本与失败/重试语义已落地（`usage_events`，见 [usage-ledger.md](usage-ledger.md)）；操作前估算、公开查询 API、额度强制仍缺。
- 速率、并发、日任务量、存储配额的强制边界与观测。
- 备份恢复演练：库 + COS；恢复后作品与图像可读。

### 工程后续切片（不挡邀请试用话术）

- 导出制作包仍在 Postgres `exports.content`；迁出 Object存储为 INFRA-02 后续切片。
- 预签名 URL 读路径：非本期默认（仍代理流）。

## 对象存储

- 决策：[ADR-004](decisions/ADR-004-object-storage-cos.md)。
- 切流手册：[object-storage-cos-cutover.md](../delivery/object-storage-cos-cutover.md)。
- 生产：`OBJECT_STORE_BACKEND=s3`，桶示例 `manxu-assets-1255546834`；本地/CI 默认 `local`。

## 推荐顺序（在部署冻结期内）

1. 文档与对外口径对齐（本轮）；保持 CI 绿灯。  
2. 本地/CI：Dockerfile 镜像源、导出 blob 设计、AUTH-07 契约草案；用量账本 Phase 0/1 已实现（落库，无公开 API）——**不**推生产。  
3. 邀请作者在**当前线上 tag 能力**上连续做两话，验证连载复用与付费意愿。  
4. 显式解除冻结后再考虑下一版应用发布范围（仍可不含 PAGE/LETTER）。  
5. 开放注册与收费按上表缺口关闭情况决定。

## 参考资料

- [GitHub OAuth Apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
- [OWASP Email Validation](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)（邮件不宜作为高保证 OOB authenticator）
- [阿里云 DirectMail 域名](https://help.aliyun.com/zh/direct-mail/user-guide/configurations/) / [Amazon SES DMARC](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html)
