# 服务端模型配置入口

## 目标

让创作者能查看当前服务端文本与图像模型配置，同时保证供应商密钥不会进入浏览器；明确区分配置存在与 provider 已实际接入。

## 范围

- 使用根目录 `.env` 配置文本/图像 provider、模型 ID、Base URL、API key 与图像参数。
- 增加只读 `GET /model-config`，仅暴露配置值与密钥是否存在，不返回密钥。
- 将工作区模型设置入口连接到该 API，并标注 provider 接入状态。
- OpenAPI YAML 先行并生成 TypeScript API 类型。

## 任务

- [x] 增加后端模型配置字段与环境变量示例。
- [x] 在 OpenAPI 中定义模型配置摘要接口并生成前端类型。
- [x] 增加工作区模型设置入口与服务端状态面板。
- [x] 增加配置响应不泄露密钥的后端测试。
- [x] 运行 OpenAPI lint、前端 lint/typecheck/build、后端契约与系统路由测试。
- [x] 更新项目状态。

## 验收与限制

- 密钥只存在于服务端环境配置；API 只返回布尔配置状态。
- 当前 provider 尚未接入生成任务，状态面板会明确说明生成仍返回演示结果。
- 验证结果：前端 lint 通过（3 条既有 Fast Refresh warning），typecheck/build 通过；后端相关测试 4 项通过；OpenAPI lint 通过。
