# 0026 字效主编辑进工作室

## Goal

LETTER 真源不变（仍挂 PageSlot）；**主编辑面改为工作室「制作预览」条漫**；成稿排版退回页结构；Studio/EXP 叠字优先 LETTER，无字效时才回退分镜对白占位。不含 PUBLISH。

## Product (docs)

- [x] PRD：LETTER MVP 钉死主编辑面；LETTER-03；EXP-01 叠字规则
- [x] user-flows / screens A2 入口改 Studio
- [x] status / roadmap 下一步更新

## Implementation

- [x] 共享 `useEpisodeLayoutLettering` + 工作室条漫叠字（LETTER / 对白回退）
- [x] `ComicPreviewDialog`：种气泡 + 编辑字效（主完成面）
- [x] 成稿排版页：字效侧栏降级，引导回工作室
- [x] EXP PNG：有 LETTER 则烘焙 LETTER，否则分镜对白
- [x] OpenAPI 导出说明同步
- [x] `test_export_lettering_bake.py`
- [x] 本地手验（2026-10-17）：登录 → 制作预览改字持久化 → 画布叠字 → 成稿排版降级 → EXP PNG 成功；前端临时端口 5174（本机 5173 被 AgentHub 占用）；**不部署生产**
- [x] 体验小修：新增气泡优先分镜对白；占位文案可辨；「替换已有」露出并确认后 `replace_existing`

## Out of scope

PUBLISH；爆炸泡/字体上传；生产部署；拖拽几何（可继续用 % 表单）。

## Gate

生产继续冻结于 `v0.1.0-storyboard`。
