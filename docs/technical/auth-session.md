# 登录会话与鉴权机制

当前实现是服务端会话（opaque token），不是 JWT。

1. GitHub OAuth callback 校验一次性、短时有效的 `state`，用 GitHub 数字用户 ID 识别账户。
2. 登录成功后生成高熵随机 session token；数据库只保存 `sha256(token)`，原 token 只写入 `HttpOnly` 的 `manxu_session` Cookie。
3. 每次受保护请求从 Cookie 取 token，哈希后查询 `account_sessions`，检查账户存在和 `expires_at`；过期会话立即删除并返回 `401 AUTH_REQUIRED`。
4. 写请求同时校验可读的 `manxu_csrf` Cookie 与 `X-CSRF-Token` 请求头，使用常量时间比较；失败返回 `403 CSRF_INVALID`。
5. 登出删除服务端会话记录，并清除 session 与 CSRF Cookie。

Cookie 默认 `SameSite=Lax`；生产环境应设置 `SESSION_COOKIE_SECURE=true` 并只使用 HTTPS。会话目前是单设备 token，尚未提供“查看设备/撤销全部会话”页面；开放多账户注册前应补充账户所有权校验、会话管理和邮箱验证码登录方案。
