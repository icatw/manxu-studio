# 漫序 Studio 文档

漫序 Studio 是面向独立漫剧创作者和小型工作室的 AI 预制作工作台。文档记录产品范围、交互流程、领域数据和技术决策，作为后续实现与验收的共同依据。

## 文档索引

### 产品

- [产品简报](product/brief.md)：目标用户、问题、定位和产品原则。
- [需求文档](product/prd.md)：目标、范围、功能需求、非目标和验收条件。
- [长期目标：完整漫画 / 成刊层](product/roadmap-complete-comic.md)：预制作之上的成刊愿景与分期（规划中，不授权实现）。
- [核心用户流程](product/user-flows.md)：从故事创意到分镜交付的主路径（含成刊草案，标注长期）。

### 设计

- [页面与状态说明](design/screens.md)：主要页面、布局职责和关键状态。

### 技术

- [API 契约与变更流程](api/README.md)：YAML 先行、需求门禁、评审和契约验证规则。
- [OpenAPI 契约](api/openapi.yaml)：前后端共同遵守的初版 HTTP API 契约。
- [API 响应与日志规范](technical/api-errors-and-logging.md)：错误响应、request ID、结构化日志和本地轮转策略。
- [架构与技术选型](technical/architecture.md)：前后端边界、推荐技术栈和待决事项。
- [领域模型](technical/domain-model.md)：核心实体、关系和生命周期。
- [SaaS 多账户化准备](technical/saas-readiness.md)：开放注册前的租户隔离、安全和运行能力清单。
- [测试策略调研](technical/testing-strategy.md)：需求驱动的测试设计、API/E2E 覆盖和 Docker Playground 待办。
- [AI 生成管线](technical/ai-pipeline.md)：模型职责、任务状态、输入输出和失败处理。
- [技术决策记录](technical/decisions/README.md)：技术栈与 YAML 契约决策状态及理由。

### 知识与流程

- [项目知识库索引](knowledge/README.md)：领域词汇、决策和进度事实源。
- [Harness 工作区](../.harness/README.md)：AI-native 工作流、进度和执行计划统一入口。

### 交付

- [验收清单](delivery/acceptance.md)：端到端验收条件和演示路径。
- [单机 VPS 部署](delivery/deploy-vps.md)：Compose + Caddy 一键部署、备份与更新。
- [腾讯云共用机 nginx 部署](delivery/deploy-tencent-nginx.md)：与现有站点共存时的 Compose + 主机 nginx。
- [COS 对象存储切流](delivery/object-storage-cos-cutover.md)：卷 → 腾讯云 COS 迁移、切流与回滚（INFRA-02）。

## 状态

当前已确认交付聚焦 **预制作工作台**（部署与演示路径已可用）。**完整漫画 / 成刊** 记为长期目标，见 [roadmap-complete-comic.md](product/roadmap-complete-comic.md)；`proposed` 需求在确认前不得当作实现授权。对象存储、托管库等基础设施仍按 ADR 与 SaaS 清单推进。技术实现应遵守 [架构决策](technical/architecture.md)，变更关键选择时在 `technical/decisions/` 记录原因。
