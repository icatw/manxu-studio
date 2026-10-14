# API 响应与请求日志

## 目标

将所有 JSON 成功与错误响应统一为 `code/message/data/request_id`，保留 HTTP status 语义及 204、OAuth 重定向、文件响应。为每个请求提供可关联、脱敏的结构化日志；本地开发写轮转日志文件，生产仅输出 stdout/stderr。

## 决策

- JSON 成功 envelope 的 code 为 `OK`；错误使用稳定应用码，错误的 `data` 为 null，422 附 `errors`。
- 服务端生成 request ID；响应体及 `X-Request-ID` 响应头使用同一值。
- 标准库 `logging` 输出 JSON Lines。开发环境同时控制台与 `backend/.data/logs/api.jsonl`，10 MiB 轮转、保留 5 个文件；生产 stdout/stderr。
- 不记录 cookie、CSRF、Authorization、模型密钥、OAuth 参数或请求/响应正文。
- 工作区写请求的 curl 调用补齐 `Content-Type: application/json` 和 `X-CSRF-Token`；前端继续自动添加 CSRF 请求头。

## 执行清单

- [x] 更新 OpenAPI JSON 成功/错误 schemas，保留非 JSON 响应。
- [x] 实现响应封套、异常处理、request ID 和访问日志。
- [x] 更新前端响应解析和错误展示，重新生成 OpenAPI 类型。
- [x] 增加后端异常/日志测试和前端契约调用测试。
- [x] 运行契约 lint、类型生成检查、后端和前端质量门禁；手工验证创建项目。
- [x] 更新 `.harness/status.md`，将本计划移至 completed。

## 验收

- 所有 JSON API 响应具有相同 envelope；body 中 request ID 与响应头一致。
- HTTP status 保持语义；204、重定向、图片和下载响应不被包装。
- 未预期异常只向客户端返回通用错误，不泄漏内部详情；服务端记录 traceback。
- 本地日志成功轮转且不包含凭据或请求正文；生产模式不创建本地日志文件。
- OpenAPI、FastAPI 运行时和前端生成类型一致。
