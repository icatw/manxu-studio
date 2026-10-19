# 0035 — 场景空态 CTA + 管线解耦

## Goal

Scenes are independently completable: empty state can generate; warm storyboard pipeline can fill empty scene library without regenerating characters.

## Approach

1. `story_pipeline`: run scenes stage whenever not checkpointed; if `regenerate_characters=false`, only run scenes when project currently has zero scenes (append). When regenerating characters, keep existing scene stage behavior.
2. Scene board: empty primary CTA; warm append + missing refs + optional rebuild confirm.
3. Storyboard soft banner when `scenes.length === 0`.
4. Pass `episode_id` into scene-generations from UI for synopsis context.

## Done when

- [x] Pipeline test: warm path fills empty scenes; skips scenes when library already non-empty
- [x] Scene board empty/warm CTAs
- [x] Storyboard soft prompt
- [x] Frontend + backend checks (pipeline 9; FE 25)
