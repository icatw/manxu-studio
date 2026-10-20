# 0044 — UIUX 命名收束与轻引导

## Goal

降低作者每天碰到的成稿路径摩擦：**预览/导出命名一致**、Studio **做完一话**有轻引导、成稿面有**清洁提示**。不碰生产解冻、不开 PUBLISH-02、不新增 layout 就绪聚合 API（徽标仍后置）。

## Done when

### P0 — 命名审计与收束

- [x] Studio 顶栏 / 制作预览 Dialog / 成稿排版 / 总览合集 / 阅读页：按钮·title·toast 对照「制作/成稿」二分
- [x] 总览「合集下载」说明对齐 EXP（制作向，非成稿导出）
- [x] `docs/design/screens.md` §7–9、`docs/product/user-flows.md` 与 UI 同步

### P1 — Studio「做完一话」轻引导

- [x] `EpisodeDoneHint`：分镜阶段且 ≥1 格有图时提示；会话级 `sessionStorage` 可关
- [x] CTA「成稿排版」+「知道了」；不挡出图

### P2 — 成稿清洁提示

- [x] 缺图 / 无字效计数条（可关）；统一「画面未就绪 · 回工作室出图」
- [x] 未看过成稿预览时提示先预览再导出

## Out of scope（仍开放）

每话「未排版」就绪徽标（需 layout 聚合 API）；PUBLISH-02；生产解冻。

## Verification

- [x] eslint（改动文件）+ `pnpm typecheck` + `pnpm test`（33）+ `pnpm build`
- [ ] 目检截图 `var/qa-screenshots/uiux-0044/` — 未跑浏览器目检（本地栈未起）；代码路径已落
