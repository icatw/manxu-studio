---
name: manxu-frontend
description: Build or change Manxu Studio React and TypeScript screens, hooks, state, API clients, or browser workflows. Use for frontend implementation and UI bug fixes.
---

# Manxu Frontend Engineering

Work as a senior frontend engineer inside the existing React, TypeScript, Vite, React Router, TanStack Query, and Tailwind application. Preserve its state ownership and API boundaries; do not add a second application architecture for one feature.

## Establish the workflow

- Read the confirmed PRD requirement and relevant user flow/screen documentation before changing user-visible behavior.
- Inspect the existing route, feature component, hook, API service, state reducer, and tests. Reuse their conventions where they fit.
- For work that changes a server contract, coordinate through `docs/api/openapi.yaml` first and follow `manxu-integration`.
- For changes spanning several components or a full user journey, create an active harness plan and define loading, empty, success, error, retry, and navigation outcomes before editing.

## State and component boundaries

- Treat TanStack Query as the source for server-owned data: projects, settings, assets, image versions, and task status. Use reducers or component state for transient editor state such as selection, undo history, open panels, and unsaved input.
- Do not mirror query data into local state without a deliberate editing/hydration boundary. Define when server refreshes may replace local edits and how stale data is detected.
- Keep components responsible for presentation and user intent. Put reusable interaction/state transitions in hooks and API orchestration in the existing service layer; do not make view components construct URLs, parse envelopes, or duplicate domain mapping rules.
- Keep mappings between UI types and API enums in the established domain mapping boundary. Preserve unknown server values deliberately; never silently map a meaningful value to an unrelated default.
- Avoid state flags that can contradict each other. Model mutually exclusive task/editor states as a discriminated state or derive them from one authoritative value.

### Component and module decomposition

- Split components around a clear responsibility, state owner, reusable interaction, or independently testable visual region. A component should make its inputs, emitted user intent, and owned transient state easy to identify.
- Keep route/page components as composition boundaries. Move domain transitions and asynchronous orchestration into focused hooks/services when that logic has its own lifecycle or is reused; keep one-off, local presentation logic near the view.
- Extract a child component when it has a meaningful contract or lifecycle, not merely to reduce line count. Avoid both a monolithic component that owns unrelated workflows and a tree of pass-through components with no independent role.
- Prefer explicit typed props and domain-specific names. When a component accumulates unrelated callbacks, many boolean mode props, or repeated conditional rendering for distinct workflows, use composition or separate focused components rather than adding more flags.
- Keep domain/API mapping in one boundary. Do not scatter model IDs, status translations, error mappings, route strings, or concurrency defaults across components. Use generated contract types and server-provided metadata where available.
- Keep hooks focused on one state lifecycle or interaction. Avoid a “god hook” that combines fetching, editor state, keyboard handling, persistence, and task polling when those concerns have different owners or cleanup rules.
- Optimize render behavior only after identifying a real source of repeated work or visible latency. Prefer correct state ownership and stable data flow before adding memoization; measure expensive lists/render paths before adding virtualization or caches.

## API and authentication

- Use the generated OpenAPI types and shared API client. Never hand-edit `frontend/src/lib/api/schema.d.ts`, issue ad hoc `fetch` calls for product APIs, or reimplement envelope/CSRF/session behavior in a component.
- The browser uses the HttpOnly session cookie and the shared CSRF flow. Do not move session or model credentials into `localStorage`, component state, URLs, logs, or error telemetry.
- Keep response parsing typed. Preserve stable application error code, short message, HTTP status, and request ID through service and UI boundaries.
- On `401`, follow the shared account/session gate so stale sessions return the user to sign-in. On other errors, keep the user's in-progress editor state and expose a meaningful recovery action.
- Invalidate or update the correct query keys after mutations. Avoid broad cache clears that hide ownership or stale-data bugs.

## Generation and long-running work

- Treat a generation task as server-owned durable work. The browser submits it once, displays the task's real status, and stops polling on a terminal state.
- Use bounded polling with backoff and respect retry timing where provided. Do not poll in a tight loop, create one poller per rendered component, or retry a task-creation POST because a status read failed.
- A browser `AbortController` can stop a request or polling loop; it does not cancel the server/provider job unless the API explicitly supports cancellation. Do not label local abort as remote cancellation.
- Use server-provided concurrency and supported model metadata. Do not hardcode a parallelism limit or duplicate the backend allowlist in the UI.
- Keep success, partial success with warnings, failure, timeout, and retry states distinct. Preserve prior image versions and do not show optimistic success before the durable task succeeds.

## Interaction quality

- Keep keyboard focus, labels, accessible names, disabled/loading behavior, and error announcements correct for every control.
- Preserve the established desktop-first studio layout while ensuring narrow viewports can reach primary actions and content without overlap or hidden controls.
- Prevent duplicate submissions from rapid clicks and stale callbacks from overwriting newer selection/project state.
- For autosave, define debounce, in-flight request ordering, retry behavior, and what happens when the user navigates away. A failed save must not be presented as saved.

## Verification

- Add focused tests for changed hooks/services and the state transitions they own. Cover duplicate actions, stale responses, failures, and task polling termination where relevant.
- Run `pnpm --dir frontend lint`, `pnpm --dir frontend typecheck`, `pnpm --dir frontend test`, and `pnpm --dir frontend build` for frontend changes. Run API type generation and confirm it creates no uncommitted schema diff when the contract is unchanged.
- For user-facing workflow changes, use Playwright or the connected browser to exercise the actual route and primary actions at desktop and narrow widths. A component test is not browser-flow evidence.
- Report which checks passed and which user paths were not exercised.
