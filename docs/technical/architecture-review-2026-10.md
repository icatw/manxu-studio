# 架构审查记录

## 结论

当前产品已经具备可用的账户隔离、统一响应和异步任务基础，但此前的启动边界和配置边界不完整：前端没有生产容器，API/worker 环境变量重复，Vite 代理和模型推荐值散落在源码中。此次收敛后，Compose 成为本地和演示环境的单一启动入口，PostgreSQL 保存事实数据，Redis 只负责队列，账户模型配置仍由服务端按账户保存。

## 已处理

- 前端使用独立 Nginx 容器，负责 SPA fallback 和 `/api` 反向代理。
- API 与 worker 使用同一组 Compose 环境配置，避免两套默认值漂移。
- `scripts/start.sh` 负责依赖检查、初始化 `.env` 和构建启动；`scripts/stop.sh` 负责停止服务。
- 保留 `make check`、`make test` 作为代码质量门禁，Compose 负责运行时依赖。
- 系统推荐模型仍是配置模板，不是共享 API Key。用户点击后填入当前账户表单，保存后才进入该账户的加密配置。

## 配置规则

1. 运行时配置来自环境变量；业务数据来自 PostgreSQL；短期状态和调度来自 Redis。
2. 前端不保存模型密钥，不把服务端密钥回传给浏览器。
3. 容器内部使用服务名通信，宿主机端口只用于开发访问。
4. 修改 API 契约先改 `docs/api/openapi.yaml`，再生成前端类型。
5. 新 provider 应实现独立服务接口，不在路由中增加供应商分支。

## 后续重构边界

- 将模型推荐值从组件常量提升为服务端只读 preset 接口，避免 UI 与后端模型列表漂移。（部分完成：`system_presets` + `IMAGE_MODEL_ALLOWLIST`）
- 将 `workspace.py` 拆为 projects、assets、storyboard、generation 四个路由模块。（已完成）
- 为 worker 增加独立健康检查和任务指标；不要用 API 健康状态代表 worker 健康。
- 在 CI 中执行 Compose smoke test，覆盖迁移、API、worker、前端代理和刷新恢复。
- 对象存储从本地目录升级为 S3 兼容实现（`LocalObjectStore` 协议已就位）。
- 提示词模板版本写入任务元数据表字段（模板名/版本已在 handler 结果中带回）。
