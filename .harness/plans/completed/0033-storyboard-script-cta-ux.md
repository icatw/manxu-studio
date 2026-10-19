# 0033 — 分镜脚本 CTA 收敛

## Goal

Reduce duplicate “generate storyboard script” primary actions and unify wording so users do not confuse script generation with image generation.

## Decisions

- Story page owns the forward path: cast+script (cold) or script (warm).
- When panels already exist on the story page, demote to secondary “重新生成脚本…”.
- Top toolbar: ghost “重写分镜脚本”, only on `storyboard` stage when panels already exist.
- Empty storyboard keeps one local primary “生成分镜脚本”; toolbar hidden in that state.
- Confirm whenever replacing an existing panel list (`panels.length > 0`).

## Done when

- [x] Story / toolbar / empty-state labels match the rules above
- [x] Confirm gating uses `panels.length > 0` in both story and toolbar
- [x] Frontend typecheck + unit tests pass; eslint on touched studio files clean
  (repo-wide `pnpm lint` still noisy from unrelated paths)

## Verification

- `pnpm --dir frontend typecheck` pass
- `pnpm --dir frontend test` 25 pass
- Local frontend image rebuilt for hand-check at http://localhost:5173
