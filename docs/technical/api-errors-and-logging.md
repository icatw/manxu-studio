# API 响应与日志规范

## 当前请求排查

用户给出的命令请求 `/api/v1/projects`，但包含 `--data-raw`，因此 curl 实际发出的是 `POST`，对应创建项目，不是列出项目的 `GET`。工作区写请求需要同时满足有效会话、CSRF Cookie 与匹配的 `X-CSRF-Token` 请求头；示例只带了 Cookie，没有 CSRF 请求头，按当前实现应返回 `403`。前端 API 客户端会自动从 `manxu_csrf` Cookie 读取并添加 `X-CSRF-Token`，手写 curl 不会自动执行这一步。

请求还缺少 `Content-Type: application/json`。`--data-raw` 默认使用表单内容类型，而创建接口的契约要求 JSON；补上 CSRF 后仍需加该请求头，否则请求体可能以 `422` 校验失败。正确请求形态如下，Cookie 值不要粘贴到 issue、终端共享记录或日志：

```sh
curl --request POST 'http://localhost:5173/api/v1/projects' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRF-Token: <从当前 manxu_csrf Cookie 读取>' \
  -b 'manxu_session=<session>; manxu_csrf=<csrf>' \
  --data '{"title":"重生之只有我会 AI","synopsis":"重生之只有我会 AI","genre":"都市","art_style":"电影感","aspect_ratio":"portrait"}'
```

本轮未用用户 Cookie 重放请求。无认证信息的本地诊断请求返回了 `401 {"detail":"请先使用 GitHub 登录"}`，与预期相符；当前消息没有包含实际失败响应，因此具体状态仍以浏览器 Network 的 status 和 response body 为准。

## 当前实现

- `docs/api/openapi.yaml` 为 JSON 成功和错误响应定义统一 envelope；错误使用稳定应用码，校验错误另带 `errors`。
- `backend/app/core/api_responses.py` 注册 HTTP、校验和未预期异常处理器；未预期异常只返回通用消息，服务端保留 traceback。
- `ApiResponseLoggingMiddleware` 为请求生成 request ID，在 JSON 响应体和 `X-Request-ID` 响应头复用，并记录路由、状态码、耗时和错误码。
- `backend/app/core/logging.py` 输出脱敏 JSON Lines；开发环境按 10 MiB 轮转写入 `backend/.data/logs/api.jsonl`，生产只写 stdout/stderr。
- 前端客户端在 fetch 边界解包成功 envelope；错误保留稳定错误码并把 request ID 附在提示消息中。`204`、OAuth 重定向、图片和附件下载保持原始响应。

## 建议的响应约定

HTTP status 始终表达通用语义，JSON `code` 使用稳定的应用错误标识，两者不可互相替代。建议成功 JSON 响应统一为：

```json
{
  "code": "OK",
  "message": "项目创建成功",
  "data": { "id": "...", "title": "..." },
  "request_id": "..."
}
```

错误响应继续遵循 OpenAPI 当前采用的 RFC 9457 Problem Details，扩展稳定 `code`、`request_id`，并为字段校验错误提供 `errors`。这样不另造一套错误标准，同时错误也具备用户可读消息、机器可判定代码和排障关联 ID。若产品坚持成功/错误都使用同一外层 envelope，可把 RFC 9457 字段映射为该 envelope，但需在 OpenAPI 中明确 status 与 `code` 字段语义；不要让客户端解析自然语言 `message` 来分支。

约定细节：

- `code` 是稳定枚举，例如 `OK`、`AUTH_REQUIRED`、`CSRF_INVALID`、`VALIDATION_FAILED`、`RESOURCE_NOT_FOUND`、`INTERNAL_ERROR`；不得使用 HTTP 数字码替代应用码。
- `message`/`detail` 面向用户，简短且可本地化；不能包含堆栈、SQL、文件路径、上游密钥或供应商原始敏感响应。
- 验证错误返回结构化字段路径与规则码；不要回显请求体或任意 validator 内部信息。
- `request_id` 由服务端为每个请求生成并同时放在响应头 `X-Request-ID` 与响应体中。客户端可在报错时将其提供给支持人员。
- HTTP status 与响应体 `status`（如采用 Problem Details）必须一致；成功的创建使用 `201`，无内容操作使用 `204`，认证失败 `401`，CSRF/授权拒绝 `403`，校验失败 `422`，冲突 `409`，意外异常 `500`。
- 流式响应、重定向、文件下载和 `204` 保留其 HTTP 原生形态，不强制包装。
- 通过统一响应工厂和 FastAPI `HTTPException`、`RequestValidationError`、兜底异常 handler 实现，并同步 OpenAPI YAML 和前端生成类型；避免 endpoint 各自手工组装。

## 建议的日志方案

使用 Python 标准 `logging`，在应用启动时统一配置 JSON Lines 输出。每条事件记录 UTC 时间、level、service、environment、request_id、HTTP method、路由模板、HTTP status、duration_ms、应用错误码；如已认证，可记录内部 account ID。未预期异常在服务端带 traceback 记录一次，响应只返回通用 `500` 和 request ID。

- 本地开发可同时写控制台和仓库外的可配置日志目录，例如 `backend/.data/logs/api.jsonl`；目录加入 `.gitignore`，权限限制为当前运行用户，不提供 Web 下载/访问路由。
- 本地文件必须按大小或时间轮转，并设置保留数量/天数和磁盘上限。单 worker 可用 Python `RotatingFileHandler` 或 `TimedRotatingFileHandler`；多 worker 不应让多个进程同时竞争同一个轮转文件，改为 stdout 收集，或让单独 listener/日志代理负责文件写入。
- 容器/生产环境优先写 stdout/stderr，由容器运行时或日志平台负责收集和轮转；本地文件作为开发期便利选项，不把日志文件当作唯一生产日志存储。
- 绝不记录 `Cookie`、`Set-Cookie`、`Authorization`、CSRF token、API Key、OAuth code/state、完整请求/响应 body、模型提示词或图像内容。需要关联会话时只记录短期不可逆摘要；对用户提供的文本字段做长度限制和换行符清理，防止 log injection。
- 分开 operational logs（请求、异常、延迟）和 audit events（登录/登出、配置更换、资产删除等安全事件）；审计记录使用明确事件名并控制保留期与访问权限。
- `request_id` 用于应用日志关联，不要把未经校验的客户端任意 ID 当作可信追踪 ID；可接受并校验格式，或始终由服务器生成。

## 实施顺序

1. 确认错误响应采用 RFC 9457 扩展字段；确认 JSON 成功响应采用 `code/message/data/request_id`，并保留 `204`、重定向和下载的原生响应。
2. 更新 `docs/api/openapi.yaml`，覆盖所有 endpoint 的主要 HTTP 状态及错误 schema；冻结契约后生成 TypeScript 类型。
3. FastAPI 增加 request ID middleware、结构化 logging 配置、统一异常 handlers；开发环境写入 gitignored 轮转文件并保留 stdout。
4. 前端错误处理读取稳定 `code` 和 `request_id`，提示用户时展示简洁 message，诊断时附带 request ID。
5. 增加契约与脱敏检查，验证 `401/403/422/500` 的 status/body 一致、异常返回不泄漏内部信息、日志不包含认证和模型密钥。

本方案参考 RFC 9457、FastAPI 错误处理文档、OWASP Logging Cheat Sheet 和 Python `logging.handlers` 官方文档。相关链接见下。

## 参考资料

- [RFC 9457: Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc9457)：标准错误体、扩展字段、状态码与安全注意事项。
- [FastAPI Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/)：统一处理 HTTP 异常与请求校验异常。
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)：交互标识、日志字段、敏感数据排除、访问控制与保留策略。
- [Python logging.handlers](https://docs.python.org/3/library/logging.handlers.html)：按大小/时间轮转文件，以及 QueueHandler/QueueListener。
