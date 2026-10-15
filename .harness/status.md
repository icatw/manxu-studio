# 项目状态

- 更新时间：2026-10-15
- 当前阶段：架构债清理在分支 `arch/debt-cleanup`（worktree `../kaiying-arch-debt`）已完成验证，待合入
- 代码阶段：邮箱/GitHub 登录、资源隔离、Redis/ARQ、providers/tasks 分层、应用服务层、定妆锁定、多话壳、连载层、Playwright E2E 已接入

## 当前事实

- 生成架构：`providers/` + `tasks/` 注册表；应用服务 `projects/assets/storyboard/generations/model_config/auth`；路由保持薄。
- 契约：任务状态无 `cancelled`；生成 SLA（job/stale/poll）由 Settings 统一；默认图像模型单源。
- 前端：TanStack Query 共享 `queryClient` 轮询生成任务；`lib/catalogs`；`useCurrentAccount`；Studio hydrate/autosave 抽出。
- Phase 1/2 与连载层能力仍在 main 基线上可用。
- 计划：`.harness/plans/completed/0013-architecture-debt-cleanup.md`（backend 93 / frontend 9 已通过）。

## 阶段与进度

| 阶段 | 状态 | 完成条件 |
| --- | --- | --- |
| 产品文档与初版 API 草案 | 完成 | 简报、PRD、流程、页面说明、领域模型、AI 管线和 YAML 草案已存在 |
| 需求确认与接口冻结 | 完成 | 核心工作区 + 连载层需求确认；OpenAPI 同步 |
| 工程骨架 | 完成 | 前后端可启动、锁文件/迁移/CI/契约校验就绪 |
| 创作主流程演示切片 | 完成 | 项目 → 故事 → 角色/场景 → 分镜 → 图像版本 → 预览/PNG 导出 |
| 多账户与队列 | 实现完成 | 邮箱/GitHub、隔离、Redis/ARQ |
| 自定义文本与 Qwen Image | 真实账户端到端验证完成 | 文本与图像生成持久化 |
| 生成架构分层 | 完成 | providers + task registry 合入 main（#1） |
| v0 工作区体验对齐 | 完成 | 导出双格式、构图字段、多话壳、定妆锁定、库卡片 |
| 连载层 | 完成 | 策划/伏笔/摘要/设定集/阅读页 + Playwright 核心与 live AI E2E |
| 架构债清理 | 分支完成待合入 | 服务层抽取、cancelled 移除、Query 轮询、catalogs、Studio 拆分 |
| 发布与交付 | 未开始 | 部署、演示录屏、运行说明 |

## 下一步

1. 评审并合入 `arch/debt-cleanup`（或拆 PR）。
2. 配置 GitHub OAuth 后完成双账户隔离浏览器验证。
3. 将 Playwright 核心路径纳入常规 CI（live AI 保持 opt-in）。
