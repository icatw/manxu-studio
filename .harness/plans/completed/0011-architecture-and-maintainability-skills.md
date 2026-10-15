# Architecture and Maintainability Skills

## Goal

Make the project skills more actionable for architecture, module/component boundaries, configuration ownership, conditional complexity, and evidence-based optimization.

## Scope

- Refine the architecture, frontend, backend, integration, and testing skills.
- Preserve behavior-first verification; do not add AST/source-shape gates or arbitrary file-size limits.
- Keep existing local changes and unrelated active plans untouched.

## Tasks

- [x] Add cross-layer decision principles for ownership, configuration, complexity, and optimization evidence.
- [x] Add frontend component/state decomposition criteria.
- [x] Add backend module/service decomposition and conditional-policy criteria.
- [x] Add integration guidance for single sources of truth across API/UI/worker configuration.
- [x] Add tests that prove behavior and architectural invariants without asserting source shape.
- [x] Validate all five skills and check the diff.

## Verification

- `python3 /Users/icatw/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/manxu-architecture` and the equivalent command for the other four skills: all passed.
- `git diff --check`: passed.
- Application tests were not run because this change only updates engineering guidance and the harness plan.

## Decision Log

- Do not ban `if` statements or prescribe a universal file/component line count. Require a branch or extraction only when it clarifies a domain policy, ownership boundary, independent lifecycle, or testable behavior.
- Optimize against measured user or system costs; avoid speculative caching, abstraction, and concurrency tuning.
