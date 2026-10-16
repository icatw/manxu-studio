# 0022 Personal Serial Comic Workbench Positioning

## Goal

Reposition Manxu Studio as a Chinese-first AI-assisted personal serial comic workspace for static image comics, and align product brief, PRD, user flow, roadmap, documentation index, glossary, and harness status.

## Decisions

- Product output is readable static comics, with vertical-scroll webtoon as the first reading format and paginated comics as a later option.
- The primary user is an independent comic creator or story/web-fiction author developing a recurring personal IP.
- The product differentiates through writer-controlled serial continuity, reusable canon/assets, editable storyboards, and low-cost local revisions.
- Video generation, a public reader community, real-time team collaboration, and a professional desktop publishing suite remain out of scope.
- Existing confirmed requirement IDs remain confirmed; unapproved comic page, lettering, and publication requirements remain proposed.
- Paid public SaaS readiness requires cost visibility/metering and account/data operations before launch; complex seat billing is not a prerequisite.

## Work

- [x] Rewrite product brief and PRD positioning without changing existing API contracts.
- [x] Replace the old complete-comic roadmap with a staged product and SaaS plan, gates, and validation signals.
- [x] Align the future user flow, glossary, documentation index, and current project status.
- [x] Review terminology and requirement status consistency across touched documents.

## Verification

- Documentation-only review with `rg` for stale video-oriented positioning, roadmap links, and requirement IDs; product-facing docs now consistently describe static image comics.
- Confirmed `INFRA-02` remains `confirmed`, `PAGE-*` / `LETTER-*` / `PUBLISH-*` remain `proposed`, and COS migration status matches `.harness/status.md`.
- Pre-existing edits in `backend/Dockerfile`, `frontend/Dockerfile`, and `docs/delivery/deploy-tencent-nginx.md` were not changed by this planning pass.
- No tests run; documentation review only.
