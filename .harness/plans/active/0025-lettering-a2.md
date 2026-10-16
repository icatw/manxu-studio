# 0025 A2 字效（Lettering）

## Goal

交付 LETTER-01…02：槽位锚定的气泡/旁白持久化、成稿预览叠字、从分镜对白种默认气泡；改字不重绘底图。不含 PUBLISH 成稿导出产品化。

## Contract (done)

- [x] PRD LETTER-01…02 → `confirmed` + MVP 决策与验收
- [x] user-flows / screens A2
- [x] domain-model / roadmap / brief / api README
- [x] OpenAPI `Lettering` tag：`seedLetteringFromDialogue`, `createLetteringObject`, `updateLetteringObject`, `deleteLetteringObject`；`PageSlot.lettering` / `LayoutPreviewItem.lettering` 可选数组

## Implementation (not started)

- [ ] DB：`lettering_objects` + migration；FK → `page_slots` ON DELETE CASCADE；归属经 Slot → Page → Episode → Project → Account
- [ ] Service + FastAPI routes matching operationIds；`require_slot_owner` / `require_lettering_owner`
- [ ] Layout/get/preview 响应附带 lettering（空数组亦可）
- [ ] Frontend：成稿页字效编辑 + 预览叠字 + 「从分镜生成气泡」
- [ ] 生成 TS types；ownership / seed 测试
- [ ] 手验验收条；**不部署生产**

## Out of scope

页级游离字效；字体上传；爆炸泡；PUBLISH 导出入口；生产部署。

## Gate

生产继续冻结于 `v0.1.0-storyboard`。
