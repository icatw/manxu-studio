# 0041 — 合集在线预览（COLLECT-PREVIEW）

## Goal

作品总览「合集预览」：勾选多话后连续竖读成稿条（布局+字效）；未排版话标未就绪。

## Done when

- [x] PRD COLLECT-PREVIEW-01 + OpenAPI + screens/flows
- [x] GET anthology/preview + tests
- [x] 总览入口 + preview 页
- [x] 手验多话连读 / 未就绪占位

## Verification

- Backend: `pytest tests/test_anthology_preview.py`（就绪/未排版混排、非法 id 422、归属 404、字效出现在 preview）
- Live DB: 重启：代码深渊 两话 ready + lettering；跨作 id → 422；无布局话 → `no_layout`
- UI: 总览「合集预览」→ `/anthology-preview?episodes=`；混入未排版话显示「未排版」；截图 `var/qa-screenshots/anthology-preview/`
