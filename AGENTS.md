# Repository Guide

Keep this file as a short map for coding agents. Product and technical facts live in `docs/`; read only the sources relevant to the current task.

## Source of Truth

- Product goals, confirmed scope, and requirement IDs: `docs/product/prd.md`.
- Long-term complete-comic / publication-layer vision (proposed only): `docs/product/roadmap-complete-comic.md`.
- User journeys and screen behavior: `docs/product/user-flows.md` and `docs/design/screens.md`.
- HTTP contract: `docs/api/openapi.yaml` (YAML first; do not hand-edit generated client types).
- Architecture choices and rationale: `docs/technical/architecture.md` and `docs/technical/decisions/`.
- Terms and domain vocabulary: `docs/knowledge/`.
- Current project stage and active work: `.harness/status.md` and `.harness/plans/active/`.
- Full documentation map: `docs/README.md`.

## Working Rules

- Check requirement status before implementing product behavior. `proposed` and `deferred` items are not implementation authorization.
- For API changes, update the confirmed requirement and `docs/api/openapi.yaml` before changing FastAPI or frontend code.
- For multi-file work, keep a resumable plan under `.harness/plans/active/`; record decisions, completed work, and verification there. Move finished plans to `.harness/plans/completed/`.
- Prefer existing project patterns and small changes. Add dependencies only with a recorded reason.
- Keep model-provider credentials on the backend. Validate external/model output at system boundaries.
- Run the relevant quality checks for code changes and report what was or was not verified. Update project status when a milestone changes.
- Do not duplicate full requirements, API schemas, or architecture explanations in this file. Add a link to their canonical document instead.
- Route work through the project skills: `.agents/skills/manxu-frontend/SKILL.md` for React/UI, `.agents/skills/manxu-backend/SKILL.md` for FastAPI/data/workers, `.agents/skills/manxu-integration/SKILL.md` when a change crosses layers, and `.agents/skills/manxu-testing/SKILL.md` when designing or verifying tests. Use `.agents/skills/manxu-architecture/SKILL.md` for architecture decisions and cross-layer review.

## Change Completion

A change is complete when its acceptance criteria are met, relevant checks have passed, known gaps are recorded, and the active plan/status is updated. Product/API scope changes require explicit requirement updates; do not silently widen scope while implementing.
