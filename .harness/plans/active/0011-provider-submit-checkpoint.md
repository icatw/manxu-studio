# Provider Submission Checkpoint Recovery

## Goal

Prevent duplicate image submissions when the provider accepts a request but the worker loses the remote task ID before PostgreSQL durably records it.

## Invariants

- A durable `submitting` checkpoint is committed before each billable image POST.
- A task with `submitting` and no remote task ID is ambiguous and must never POST again automatically.
- Explicit provider rejection may return the checkpoint to a retryable state.
- Failures saving the returned remote ID are treated as ambiguous and are not swallowed as partial success.
- Any remaining provider checkpoint protects a task from ordinary retry, regardless of the final generic failure code.
- Unexpected handler/provider errors must fail visibly and retain checkpoints; only classified provider rejections may become partial-success warnings.
- A confirmed remote ID is persisted from a fresh session when possible and retained for provider resume.

## Work

- [x] Extend provider checkpoint lifecycle and typed errors.
- [x] Make Qwen submit, probe, poll, download, and object-store failures classify according to whether resubmission is safe.
- [x] Persist ambiguous remote IDs in runtime and protect retries.
- [x] Update character, scene, and panel handlers plus provider-resume behavior.
- [x] Add regression tests for callback commit failure, restart with `submitting`, explicit rejection, and resume.
- [x] Run backend tests, Ruff, mypy, OpenAPI/type generation checks, and inspect CI.

## Verification

Verification: backend pytest 87 passed (4 upstream deprecation warnings); Ruff check/format and mypy passed; Redocly OpenAPI lint passed; TypeScript generation was stable (SHA-256 unchanged); frontend lint, typecheck, Vitest (9 tests), and production build passed. Added regression coverage for generic failure with a retained checkpoint, conflicting remote task ID binding, scene commit failure before provider invocation, and unexpected provider exceptions. Redis-backed worker restart and live-provider recovery were not run; these remain infrastructure/provider verification gaps.
