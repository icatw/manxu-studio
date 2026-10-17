# 0025 A2 字效（Lettering）

## Goal

交付 LETTER-01…02：槽位锚定的气泡/旁白持久化、成稿预览叠字、从分镜对白种默认气泡；改字不重绘底图。不含 PUBLISH 成稿导出产品化。

## Contract (done)

- [x] PRD LETTER-01…02 → `confirmed` + MVP 决策与验收
- [x] user-flows / screens A2
- [x] domain-model / roadmap / brief / api README
- [x] OpenAPI `Lettering` tag：`seedLetteringFromDialogue`, `createLetteringObject`, `updateLetteringObject`, `deleteLetteringObject`；`PageSlot.lettering` / `LayoutPreviewItem.lettering` 可选数组

## Implementation

- [x] DB：`lettering_objects` + migration `20261024_lettering_objects`
- [x] Service + FastAPI routes；`require_lettering_owner`
- [x] Layout/get/preview 附带 lettering
- [x] Frontend：成稿页字效编辑 + 预览叠字 + 「从分镜生成气泡」
- [x] ownership / create / seed-empty 测试（CI）
- [x] 本地手验（由 0026 工作室主编辑路径覆盖）；**不部署生产**

## Out of scope

页级游离字效；字体上传；爆炸泡；PUBLISH 导出入口；生产部署。

## Gate

生产继续冻结于 `v0.1.0-storyboard`。
