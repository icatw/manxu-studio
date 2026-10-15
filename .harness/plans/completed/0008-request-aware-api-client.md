# Request-Aware API Client

## Goal

Fix project mutations where `openapi-fetch` passes a `Request` object to the custom fetch wrapper and its method, body, and headers were not preserved.

## Acceptance

- Derive method and headers from both `Request` and `RequestInit`, with explicit init values taking precedence.
- Preserve JSON content type and attach the CSRF header to mutations constructed by `openapi-fetch`.
- Keep existing URL plus `RequestInit` behavior, non-JSON requests, and response-envelope handling intact.
- Add a regression test using the actual `Request` input shape.
- Run frontend lint, typecheck, tests, and build; record the result and archive this plan.

## Progress

- [x] Confirm the missing mutation headers are caused by dropping `Request` metadata.
- [x] Make the client request-shape aware and add regression coverage.
- [x] Run frontend quality gates and archive this plan.

## Result

- `authenticatedFetch` now merges headers from both the input `Request` and `RequestInit`, with init headers taking precedence, and reads the actual request method before deciding whether to attach CSRF.
- JSON `Content-Type` remains added for string bodies; existing Request headers preserve JSON and non-JSON content types.
- The client tests cover Request-based POST and DELETE requests, including CSRF and JSON headers.
- Vitest passed (6 tests across 2 files); ESLint, typecheck, and production build passed. ESLint has three existing Fast Refresh warnings and the build reports the existing large-chunk warning.
