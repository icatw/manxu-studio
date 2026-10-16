# 0024 A1 页与竖条排版实现

## Goal

交付 PAGE-01…03：持久化 Episode layout、竖条槽位编辑、成稿预览、重绘后默认保布局；不实现 LETTER/PUBLISH。

## Contract (done)

- [x] PRD PAGE-01…03 → `confirmed`
- [x] OpenAPI: `getEpisodeLayout`, `bootstrapEpisodeLayout`, `syncEpisodeLayout`, `getEpisodeLayoutPreview`, `reorderPages`, `reorderPageSlots`, `updatePageSlot`

## Implementation

- [ ] DB: `layout_pages`, `page_slots` + migration；归属经 Episode → Project → Account
- [ ] Service + FastAPI routes matching operationIds
- [ ] On `selectPanelImageVersion`: retarget slots with `follow_current_version`
- [ ] Generate TS types; frontend route `/projects/:id/layout/:episodeId`
- [ ] UI: bootstrap, reorder, height/gap, preview, Studio handoff
- [ ] Tests: ownership 404, bootstrap 409, sync, version follow

## Out of scope

Lettering editor; PUBLISH export; page-grid templates; production deploy.

## Verification

- `npm run api:lint` / `api:types` (frontend)
- Backend contract/route checks used by CI
- API tests for layout ownership + bootstrap
- Manual: bootstrap → edit → redraw panel → layout kept
