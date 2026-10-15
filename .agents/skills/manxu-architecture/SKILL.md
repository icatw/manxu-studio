---
name: manxu-architecture
description: Make or review architecture decisions that cross Manxu Studio frontend, API, persistence, providers, and asynchronous workers. Use before broad changes or when repeated defects point to a boundary problem.
---

# Manxu Studio Architecture Review

Act as the system architect for changes whose behavior crosses more than one layer. First establish the intended behavior and its invariants, then assign each decision to the layer that owns it. Do not equate fewer files, fewer conditionals, or more abstractions with better architecture.

## Source of truth

- Read the relevant confirmed requirement and acceptance criteria in `docs/product/prd.md`.
- Read `docs/technical/architecture.md` and the relevant decision record before changing a boundary. Treat documented choices as current unless code and status documents show that they were superseded.
- Treat `docs/api/openapi.yaml` as the manually maintained HTTP contract. Runtime OpenAPI is implementation evidence; it does not replace the YAML source.
- Use `.harness/status.md` and `.harness/plans/active/` to understand work in progress. For multi-file changes, create and maintain a resumable active plan.
- Trace actual call sites, persistence, configuration, failure handling, and tests. Do not infer behavior from a module name or a passing unit test alone.

## Architecture method

1. Describe the user-visible behavior, scope, and acceptance evidence. Identify data ownership, security, cost, concurrency, and compatibility constraints.
2. Draw the real path through UI, API contract, route, application service, database/queue, worker, provider, and result presentation. Include the paths for failure, retry, timeout, process restart, and concurrent requests.
3. Name each invariant and its owner. Keep transport concerns in routes, domain decisions in the owning service, provider protocol details in adapters, durable state in PostgreSQL, and short-lived scheduling in Redis.
4. Check whether the proposed change is idempotent and safe under duplicate requests, duplicate queue delivery, partial commits, stale browser state, and worker termination. State which outcomes are recoverable and which require user action.
5. Prefer the smallest design that preserves these invariants. Add an interface or registry when it provides a real substitution, lifecycle, or test boundary. Do not create generic layers to hide unclear ownership.
6. Update the canonical contract or decision document when behavior or architecture changes. Keep implementation, generated types, tests, and status evidence synchronized.
7. Review the complete diff against the acceptance criteria. Report concrete defects first, then test evidence and residual risks.

## Maintainable boundaries and complexity

- Assign every rule to one owner. A value that changes product behavior belongs in validated configuration or durable account/project data; a protocol invariant belongs in the adapter/contract; a derived display value should be computed rather than copied into another store.
- Keep one canonical source for each cross-layer fact, such as supported model IDs, task states, concurrency policy, error codes, and feature availability. Generate or fetch secondary representations instead of maintaining parallel frontend/backend lists.
- Split a module when it owns multiple independent reasons to change, lifecycles, external dependencies, or test boundaries. Keep cohesive code together when extraction would only move lines without clarifying ownership.
- Before adding an abstraction, name the concrete variation it supports and the caller that benefits. Prefer a direct function or explicit composition until there are multiple real policies/implementations or a meaningful isolation boundary.
- Treat conditionals as expressions of policy, not a code smell by themselves. Keep a small number of explicit branches when they describe a closed domain rule. Consider a strategy, typed dispatch table, or state machine when branches are repeated across layers, vary independently, or permit invalid combinations. Do not replace readable branches with registries solely to reduce `if` count.
- Avoid hardcoded operational/product values in call sites when operators or accounts need to change them. Put them in typed, validated settings with documented defaults and bounds. Keep true invariants and protocol constants explicit and named; do not make every constant configurable.
- Require evidence before optimization. Identify the measured bottleneck and user/system cost, establish a baseline, change one relevant boundary, then compare behavior and resource use. Avoid speculative caching, concurrency, batching, or generalized frameworks that add invalidation/recovery complexity without measured benefit.
- Review dependency direction: presentation depends on application/domain contracts; providers and storage implement ports owned by application/domain code; infrastructure details must not leak upward as branching throughout the product.
- For each proposed split or abstraction, state what becomes easier to change, test, or operate. If the benefit cannot be named, keep the existing structure.

## Specialist workflows

- For frontend implementation, follow [Manxu Frontend Engineering](../manxu-frontend/SKILL.md).
- For FastAPI, persistence, provider, or worker implementation, follow [Manxu Backend Engineering](../manxu-backend/SKILL.md).
- For a change crossing UI and API, follow [Manxu Integration Engineering](../manxu-integration/SKILL.md) in addition to the relevant implementation skill.
- For test design, regression review, or release evidence, follow [Manxu Test Engineering](../manxu-testing/SKILL.md).

## Review standard

- Reject a change when its acceptance story cannot be traced from the UI to durable state and back, or when failure/recovery behavior is implicit.
- Do not accept “CI passed” as proof for behavior that CI does not exercise. Identify whether evidence is static analysis, a unit test, an API contract test, a database/queue integration test, a browser test, or a live-provider test.
- Do not add a static import/AST rule as a substitute for testing runtime invariants. Static checks are appropriate only for simple, deterministic policies that cannot be established by behavior tests.
- When evidence is missing, say exactly which user path or failure mode remains unverified. Do not silently broaden scope to fix unrelated architecture debt.
