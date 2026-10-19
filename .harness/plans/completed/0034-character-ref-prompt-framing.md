# 0034 — 角色参考图提示词：脸部入画与字段硬绑定

## Problem

Character reference images vary wildly: cropped heads, clothing/hair ignoring form fields, and non-corporeal cast forced into full-body anime. Root cause: final image prompt mostly trusts freeform `profile.image_prompt` with weak framing constraints.

## Approach

- Build render prompt from live profile fields (appearance / hairstyle / outfit / traits).
- Hard framing: head+face visible, full body with headroom, no torso-only crop.
- Branch non-corporeal profiles away from “全身立绘”.
- Tighten `CHARACTER_DRAFT` instructions for `reference_image_prompt`.

## Done when

- [x] Prompt builder unit-tested
- [x] Character image path uses builder
- [x] Relevant workspace tests still pass (17)

## Notes

Existing references keep old images until the user clicks「重出参考图」/「生成缺失参考图」.
