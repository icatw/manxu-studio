# Real AI Character Generation

## Goal

Make role generation visibly and persistently AI-backed, remove misleading demo-source labels from the workspace, and verify one real text plus image generation using the configured account providers.

## Scope

- Record whether a character profile was AI-drafted or manually authored in the API contract and persisted profile.
- Report actionable generation progress and never present placeholder/sample images as AI results.
- Use the account's configured text and Qwen Image credentials only on the backend.
- Run backend/frontend quality checks and a browser workflow against the rebuilt local Compose services.

## Progress

- [x] Confirm the live browser was showing legacy demo output while local source changes were not deployed.
- [x] Confirm the active account has text and image model credentials configured without reading secret values.
- [x] Update OpenAPI and generated types for character draft provenance.
- [x] Implement progress-aware text and image generation, and honest UI source labels.
- [x] Add focused provider workflow tests and run quality checks.
- [x] Rebuild services and verify a real character generation in the browser.

## Verification Notes

The temporary browser verification project remains in the local account workspace. It contains the verified AI character, image, scenes, and storyboard, so it was retained as a reviewable result.

- Text and Qwen Image tasks succeeded with the account's saved models; the character task took about 80 seconds.
- Browser reload initially exposed a strict scene-profile validation error. The scene name is now stored only in its dedicated field, and reads ignore the legacy duplicate field.
- The resulting character reference image is available at `/api/v1/assets/86f6ed3a-aff0-406a-8d30-9d26bb1c8642` and persisted in the image volume.
