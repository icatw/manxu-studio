# Account Settings and Image Endpoint

## Goal

Move account identity and AI provider settings into a global settings page, reachable from the workspace sidebar and project library. Allow the signed-in account to edit its display name and Qwen Image API base URL.

## Scope

- Keep the GitHub login and avatar as provider identity; persist an editable display name.
- Move text model and Qwen Image configuration out of the project toolbar into account settings.
- Save Qwen Image Base URL per account and validate it as a public HTTPS endpoint.
- Keep OpenAPI YAML as the contract source and regenerate TypeScript types after contract changes.
- Explain that the supplied `compatible-mode/v1` URL is an OpenAI-compatible workspace endpoint; the Qwen Image provider maps it to the asynchronous `/api/v1` API path.

## Progress

- [x] Update PRD and OpenAPI contract first.
- [x] Regenerate frontend API types.
- [x] Add account display name and image Base URL persistence.
- [x] Build the global settings page and navigation entry points.
- [x] Verify API/UI quality gates; protected browser workflow remains pending a signed-in browser session.
