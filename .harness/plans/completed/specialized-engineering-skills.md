# Specialized Engineering Skills

## Goal

Replace a shallow AST architecture check with detailed Manxu Studio workflows for architecture, frontend, backend, integration, and testing. Keep CI focused on observable behavior and normal quality gates.

## Tasks

- [x] Inspect project architecture, API contract, current CI, and existing tests.
- [x] Define specialist skill boundaries and project-specific constraints.
- [x] Remove the AST script and its CI/local-check references.
- [x] Validate every skill and verify no executable AST-gate reference remains.

## Review Evidence

- PR #1 at `d8171906d05f297611bb0e3182a37cbc390dac2d` has green CI and GitHub reports merge state `CLEAN`.
- Review found an ARQ timeout/requeue result-retention issue and a non-idempotent story pipeline replay. These block merge; see review findings in the task response.

## Verification

- Skill creator `quick_validate.py` passed for all five project skills.
- `git diff --check` passed.
- PR CI status was read from GitHub: backend and frontend jobs passed on both reported workflow runs.
- ARQ `enqueue_job` implementation was inspected in the locked environment; it rejects IDs present in either the queue job key or result key. Worker default result retention is 3600 seconds.
- No application test suite was run for the skill-only changes.
