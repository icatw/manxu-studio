# 0027 A3 成稿导出（PUBLISH-01）

## Goal

交付 PUBLISH-01：本话按 Page/Slot + Lettering 导出成稿 PNG / 分页 ZIP / PDF；与 EXP「制作导出」双轨文案。不含 PUBLISH-02。

## Contract

- [x] PRD PUBLISH-01 → `confirmed` + MVP / 验收
- [x] user-flows / screens A3
- [x] OpenAPI `Publish`：`createEpisodeManuscriptExport`；`ManuscriptExportRequest`
- [x] 生成 `schema.d.ts`

## Implementation

- [x] Backend：enqueue `scope=manuscript`；布局序合成；仅 Lettering 烘焙；无布局 409
- [x] Frontend：成稿排版「导出成稿 ▾」
- [x] 单元测试（`test_export_manuscript.py`）；本地镜像已重建（`FRONTEND_PORT=5174`）
- [x] 手验通过（2026-10-17）：成稿排版导出 + 与制作导出文案区分；**不部署生产**

## Out of scope

PUBLISH-02；CBZ；合集成稿；生产解冻。

## Gate

生产继续冻结于 `v0.1.0-storyboard`。
