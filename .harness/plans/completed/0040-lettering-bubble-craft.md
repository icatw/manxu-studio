# 0040 — 成稿字效可读性（LETTER craft）

## Goal

种泡文案与几何可读：禁「无对白。」进成稿、拆泡合并 Name 行、剥说话人前缀、双泡左右错开加宽；烘焙跳过壳/草稿占位。不改气泡外形体系、不做躲脸。

## Done when

- [x] PRD LETTER-04/05 + 种泡摆位/烘焙跳过文案更新；OpenAPI/screens/flows
- [x] `lettering.py` 拆泡/剥前缀/壳扩展/双泡几何；export 跳过非内容
- [x] 前端模板宽度 + overlay 中文折行
- [x] 单测绿（split/shell/geometry/export）；已有脏字效需 `replace_existing` 重种

## Notes

- 已有脏字效不自动迁移；制作预览「从分镜生成气泡」勾选替换后重建。
- 编辑器仍可见草稿占位；仅烘焙跳过。
- Verified: unit suite (23); live replace-reseed on episode「完美算法」— slot2 双泡左右无 Name: 前缀，slot3「无对白。」清空；bake 跳过壳/草稿。
- Follow-up fix: `replace_existing` 在 prepared 为空时仍先删旧字效（否则壳泡残留）。
