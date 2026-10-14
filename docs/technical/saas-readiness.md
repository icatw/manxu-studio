# SaaS 多账户化准备

## 结论

GitHub OAuth 与账户级模型配置适合作为 SaaS 的基础。当前代码已经有账户、会话、每账户模型配置和项目所有者字段，但登录入口仍锁定首个账户，且部分业务接口尚未按当前账户校验项目所有权。**在资源级隔离完成前不得开放注册。**

## 当前可复用部分

- GitHub OAuth 回调以 GitHub 数字用户 ID 作为身份标识；账户资料保存登录名、头像和可编辑昵称。
- HttpOnly 会话 Cookie、CSRF 校验和服务端会话过期检查已接入。
- `account_model_configs.account_id` 是主键；文本与图像 API Key 分别加密保存，模型配置接口按当前账户读取。
- `projects.owner_id` 已存在，可作为所有创作数据向账户归属的根。

## 开放注册前的阻断项

### P0：完成所有权校验

当前项目列表和创建仍从单行 `account_registry` 取所有者；其他项目、故事单元、角色、场景、分镜、版本、生成任务、图片资源与导出接口主要验证“已登录”，并未系统地验证资源所属项目归当前会话账户。仅允许多个 GitHub 用户 OAuth 登录会造成跨账户读取或修改风险。

改造要求：

- 请求处理从有效会话取得 `current_account.id`，禁止把单账户注册表当作数据所有者来源。
- 所有项目查询同时限定 `ProjectRecord.owner_id == current_account.id`。
- 所有子资源通过所属 Episode/Project 向上校验账户归属；不存在或不属于当前账户时统一返回 404。
- 任务轮询、重试、图片查看/下载、版本选择和导出下载必须执行相同的所有权检查。
- 增加双账户 API 测试，覆盖跨账户读取、更新、删除、任务查询、图片和导出；还要验证同一 ID 在本账户内可正常操作。

### P1：登录与注册方式

产品方向建议为：**邮箱 + 验证码是主要登录/注册方式；GitHub、Google 等第三方登录作为下方的可选按钮。** 邮箱验证码验证成功后，如果规范化邮箱尚无身份记录则创建账户，如果已有则登录；用户不需要先判断自己属于“登录”还是“注册”，也不需要设置密码。

#### 前端流程

登录页采用一个清楚的顺序：

1. 标题“登录或注册”，填写邮箱并请求验证码。
2. 验证码发送后在同一流程输入验证码，支持粘贴、自动前进/退格、显示目标邮箱、倒计时重发和更正邮箱。
3. 验证成功后进入项目库；新账户同时完成注册。
4. 分隔线下显示“使用 GitHub 继续”等第三方按钮。按钮只有对应 provider 已在部署环境启用时才显示。

账户设置显示已验证邮箱和已绑定的第三方身份。绑定身份必须由已登录账户主动发起；解绑前确认账户仍保留至少一种可用登录/恢复方式。不能仅因为 GitHub 返回的邮箱与站内邮箱相同，就静默合并两个账户。

#### 后端流程与候选 API

以下为方案草案，不直接修改当前冻结的 `openapi.yaml`。进入实现前，应在 PRD 建立并确认需求 ID，再按 YAML-first 流程评审、冻结契约和生成前端类型。

| 操作 | 候选路由 | 行为 |
| --- | --- | --- |
| 发送邮箱验证码 | `POST /auth/email/code` | 接受邮箱；对已存在/不存在邮箱返回相同的 `202` 文案，避免账户枚举；验证码写入投递队列 |
| 验证码登录/注册 | `POST /auth/email/verify` | 验证挑战后原子消费；按规范化邮箱查询或创建身份/账户，创建会话并设置 Cookie |
| 第三方登录开始 | `GET /auth/providers/{provider}/start` | 生成一次性 state，保存 provider 和 login/link intent，重定向至 provider |
| 第三方回调 | `GET /auth/providers/{provider}/callback` | 验证 state、交换 code、验证 provider 身份声明；按稳定 subject 查询或创建身份/账户 |
| 查询已绑定身份 | `GET /auth/identities` | 返回当前账户的邮箱与 provider 摘要，不返回 OAuth token |
| 发起/确认身份绑定 | `POST /auth/providers/{provider}/link` 及 OAuth callback | 需要现有会话和近期重新验证；唯一约束冲突时拒绝绑定，不自动合并账户 |
| 解绑身份 | `DELETE /auth/identities/{identity_id}` | CSRF 校验；只有剩余至少一个可用认证方式时才允许解绑 |

邮箱请求和验证码校验需分别限流，至少组合 IP、规范化邮箱、设备/会话维度；验证码短时有效、单次使用、限制失败次数和重发频率。数据库只保存带服务端 pepper 的验证码摘要，不存明文；新验证码不能重置累计失败次数。发送接口不暴露邮箱是否已注册，日志不得记录验证码或完整登录链接。邮件投递应走后台队列，接口快速返回，避免同步邮件服务延迟拖垮登录请求。

#### 建议的数据模型

- `accounts`：产品账户主体，存 `id`、昵称、头像、状态和创建时间，不把 `github_id` 设成账户必填字段。
- `auth_identities`：存 `account_id`、`provider`、`provider_subject`、原始/规范化邮箱（可选）、邮箱验证时间和绑定时间；对 `(provider, provider_subject)` 建唯一约束。邮箱身份 subject 使用明确规范化策略后的邮箱（保留显示值、域名小写，不做 Gmail 点号等 provider 专有转换）；GitHub 使用稳定数字用户 ID；OIDC provider 使用经过 issuer 校验的 `sub`，不使用可变用户名或邮箱作为 provider subject。
- `email_login_challenges`：存规范化邮箱、用途、验证码 HMAC 摘要、过期时间、失败次数、发送时间、消费时间和必要的反滥用统计；通过事务/条件更新保证一次性消费。
- `account_sessions`：继续以不可逆 token hash 存会话，并允许按账户撤销；生产 Cookie 使用 HTTPS、`HttpOnly`、`Secure`、`SameSite=Lax`，写操作继续执行 CSRF 校验。

迁移时保留现有 `accounts.id`，把现有每个 `github_id` 回填为 `auth_identities(provider='github', provider_subject=<id>)`，以免改变项目 owner、模型配置和会话的外键。验证回填完整后再让 `github_id` 可空/移除，并逐步移除单行 `account_registry`。新用户的邮箱身份和 `accounts`、空模型配置应在一个数据库事务中创建；并发注册靠唯一约束和冲突后重新读取保证幂等。

#### Provider 安全边界

所有 provider 都由 FastAPI 完成授权码交换和身份验证，浏览器不接触 client secret 或 provider access token。state 必须随机、一次性、过期、与 provider 及登录/绑定意图关联；callback URL 精确匹配，不启用 wildcard。GitHub 用数字用户 ID 识别账户，尽量只申请身份所需 scope。Google 等 OIDC provider 还要验证 ID token 签名、issuer、audience、有效期及 nonce，并以 `sub` 作为身份键。

邮箱验证码是产品主登录手段，但只代表用户能访问该邮箱，存在邮箱账户被盗导致漫川账户失陷的风险；它不是 MFA，也不具备抗钓鱼能力。NIST SP 800-63B 明确不允许 email 作为 out-of-band authenticator；因此本方案是产品便利性取舍，不应宣称符合 NIST 高保证等级。其对允许使用的 out-of-band authenticator 还要求短时、一次性、至少六位十进制数字并有限流。对本产品邮件验证码的建议初始参数是 6 位、5 分钟有效、成功后立即消费、最多 5 次错误尝试、60 秒重发间隔，并对邮箱/IP 设滚动速率限制；上线前仍需按实际攻击面和投递延迟确认。

若第三方登录身份未绑定，但 provider 返回的已验证邮箱与现有邮箱身份冲突，不得直接合并或创建歧义账户；提示用户先用邮箱验证码登录原账户，再从设置页绑定该 provider。GitHub 用户隐藏邮箱时则只按 GitHub 数字 ID 创建/查找身份。

### P1：邮件投递服务

定义后端 `EmailSender` 接口，将验证码模板、队列、重试和投递事件与厂商 SDK 解耦。服务商尚不预先锁定；需要根据部署地域、主要邮箱覆盖、送达率/延迟、数据处理位置、费用、退信与投诉 webhook、生产发送审批进行实测后选择。候选可以比较阿里云 DirectMail 和 Amazon SES，但同一时刻由一个已验证 sender domain 发信。

正式开放前准备专用发信子域和发件地址，完成服务商要求的域名验证以及 SPF、DKIM、DMARC 配置；开发环境使用本地邮件捕获器，不向真实用户发送测试验证码。邮件只包含验证码和失效提示，不包含模型配置、项目内容或其他账户数据。

### P1：每账户模型配置与成本控制

模型 API Key 保持每账户 BYOK，并确保只能由服务端解密和调用。轮换 `MODEL_ENCRYPTION_KEY` 需要明确的重加密方案；生产宜使用云密钥管理服务或 envelope encryption。公开注册后需限制端点数量/协议、请求大小、测试频率、生成并发、每日任务量和账户存储占用，避免模型测试或生成接口被滥用。BYOK 并不能消除应用自身的网络、存储和 worker 成本。

### P1：SaaS 存储与后台任务

- 将本地 `IMAGE_STORAGE_DIR` 迁移到私有对象存储，数据库只存对象键和元数据；下载需校验账户所有权后返回短时签名 URL 或代理流。
- 将 FastAPI `BackgroundTasks` 换成可恢复的任务 worker/队列；任务记录需要带账户归属、幂等键、重试策略、并发配额和用量统计。
- 为账户删除定义项目、模型密钥、任务、图片和导出数据的保留/清理策略。

### P2：产品与运营准备

公开注册前发布隐私政策和服务条款，说明邮箱及第三方登录数据、模型凭据加密、图像存储和第三方模型调用。初期可通过邀请码或账户 allowlist 做封闭测试；准备好监控、限流、客服/滥用处理和备份恢复后再开放自助注册。团队/组织、订阅与付费属于后续产品范围，不是实现多个人账户隔离的前置条件。

## 推荐实施顺序

1. 租户边界重构与双账户隔离测试，保持注册关闭。
2. 邮箱验证码自动注册与第三方 identity mapping、并发安全、账户级模型配置端到端验证。
3. 持久任务 worker、对象存储、配额/速率限制和用量可观测性。
4. 邀请制试运行，完成安全审查与隐私/删除流程。
5. 根据成本与运维能力逐步开放注册；按实际使用再决定账单和团队功能。

## 参考资料

- [GitHub OAuth Apps 授权与 Web application flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)：授权码流程、回调 URL 和 state。
- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)：后端 server flow、state/nonce 和 ID token 验证。
- [OWASP Email Validation and Verification Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html)：邮箱规范化、账户枚举和身份绑定风险。
- [NIST SP 800-63B Authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)：邮件不应用作 out-of-band authenticator；该标准对可用 OOB 验证码规定时效、一次性、最小长度和限流，也区分邮箱地址验证与登录认证。
- [阿里云 DirectMail 发信域名配置](https://help.aliyun.com/zh/direct-mail/user-guide/configurations/) 与 [Amazon SES DMARC 指南](https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html)：发件域名身份验证、SPF/DKIM/DMARC 配置。

## 已知本地 OAuth 故障

2026-10-14 本地 GitHub OAuth callback 返回 500 的根因是数据库迁移落后于代码：数据库版本为 `20261014_account_workbench`，应用已读取 `accounts.display_name`，但该列由后续 `20261015_account_settings` 迁移新增。升级到最新 Alembic revision 后即可与当前账户模型匹配。排查 OAuth 500 时先比较 `alembic current` 和 `alembic heads`，避免重放已使用的 OAuth 授权码。
