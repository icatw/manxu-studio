# ADR-002：YAML 先行的 API 契约

- 状态：`accepted`
- 日期：2026-10-14
- 决策人：用户确认 YAML 先行

## 决定建议

将 `docs/api/openapi.yaml` 作为唯一人工维护的 HTTP API 契约源。需求确认后先更新 YAML；前端从 YAML 生成类型；FastAPI schema/route 和契约测试证明服务端符合 YAML。运行时自动导出的 OpenAPI 不能覆盖源契约。

## 理由

- 产品、前端和后端可以在接口尚未实现时审阅同一个具体请求/响应契约。
- YAML 结构可被 OpenAPI linter、类型生成器和契约测试工具读取。
- 需求 ID 可以挂在 OpenAPI operation 上，追踪需求到接口、代码和验收。

## 约束

- 未确认需求不进入正式契约；当前 OpenAPI 文件是 `draft`。
- 公开 API 不暴露供应商 SDK、模型供应商密钥或供应商原始任务协议。
- 契约变更需说明兼容性，并同步更新验收检查。

## 参考

- [FastAPI 自动生成 OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [openapi-typescript 使用 OpenAPI schema 生成类型](https://openapi-ts.dev/introduction)
- [API 契约流程](../../api/README.md)
