# Account Identity Status and Browser E2E

## Goal

Correctly represent GitHub OAuth identity verification in account settings and run the core signed-in browser workflow against the local app.

## Acceptance

- GitHub identity verification reflects successful OAuth authentication; email verification continues to reflect successful email-code verification.
- OpenAPI explains the `verified` meaning without changing response shape.
- Add focused regression coverage for both providers.
- In a real browser session, verify settings identity status, create a disposable project, open its workspace, and delete it; do not modify existing projects or provider credentials.
- Record browser findings and quality gate results.

## Results

- GitHub identity status was corrected: successful OAuth authentication marks GitHub verified; email identity still uses the email-code verification timestamp. Three backend regression cases cover the provider-specific semantics.
- The profile displays one GitHub login method with status `已验证`.
- Browser E2E passed: project creation returned HTTP 201 with JSON and CSRF headers, opened the workspace, autosaved a story edit, restored it after refresh, and deleted the disposable project. The project disappeared from the UI and a read-only database query confirmed no matching row. Existing projects were preserved.
- The delete confirmation now uses an accessible in-app alert dialog instead of a native JavaScript dialog, which had stalled the locked Chrome automation session.
- Text and image models remain unconfigured for this account, so no paid provider generation was invoked.
- Verification passed: backend pytest (30), Ruff, mypy, OpenAPI lint, frontend Vitest (8), lint, typecheck, and production build. Frontend lint reports three existing Fast Refresh warnings; the build reports a large-bundle warning.
