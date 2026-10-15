# Project Architecture Skill and CI Gate

## Goal

Give coding agents a repeatable architecture workflow and make the initial model-provider boundary mechanically enforceable in CI.

## Scope

- Add a project-local `manxu-architecture` skill.
- Add a standard-library AST check for model provider imports.
- Run the check in backend CI and `make check`; link the skill from `AGENTS.md`.

## Tasks

- [x] Inspect current project instructions, CI, and provider call sites.
- [x] Add the project skill and repository entry point.
- [x] Add and wire the architecture check.
- [x] Run the architecture check, validate the skill, and check CI YAML.

## Verification

- `uv run --directory backend python ../scripts/check_architecture.py`: passed.
- Synthetic AST import check: detected a direct provider adapter import.
- Skill creator `quick_validate.py`: passed.
- Ruff check and format check for `scripts/check_architecture.py`: passed.
- CI workflow YAML parsed successfully.
- Full backend `ruff format --check .` remains failing on seven pre-existing files; those files were outside this change and were left untouched.
- Backend pytest and full frontend/backend gates were not run.

## Follow-up (2026-10-15)

The AST import-boundary gate was removed after review because it enforced source shape rather than runtime invariants. It was replaced by the detailed frontend, backend, integration, and testing skills under `.agents/skills/`; CI continues to gate actual lint, type, contract-generation, build, and behavior-test results.
