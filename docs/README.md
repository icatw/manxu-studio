# 漫序 Studio 文档

漫序 Studio 面向个人连载漫画创作者，帮助作者管理作品连续性并制作静态图片漫画。文档记录产品范围、用户流程、路线、领域数据和技术决策，作为实现与验收依据。

## 文档索引

### 产品

- [产品简报](product/brief.md)：目标用户、问题、定位和产品原则。
- [需求文档](product/prd.md)：目标、范围、功能需求、非目标和验收条件。
- [个人连载漫画工作台路线图](product/roadmap-complete-comic.md)：产品定位、市场观察、SaaS 阶段、验证门槛与完整产品路线。
- [核心用户流程](product/user-flows.md)：当前已交付流程与规划中的完整漫画创作流程。

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

当前已确认交付覆盖个人连载工作台的作品/话管理、连续性资料、分镜、静态画格和制作导出。完整可编辑页面、独立对白层及公开发布仍须通过 PRD `proposed` 需求门禁；实现前应先验证目标作者需求并按 YAML-first 更新契约。SaaS 基础设施按项目状态和 ADR 推进。技术实现应遵守 [架构决策](technical/architecture.md)，关键选择记录在 `technical/decisions/`。
