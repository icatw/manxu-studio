# 0038 — 第二话故事真源（EP2-OUTLINE / CONTINUITY）

## Goal

续写第 N 话时用「规划话大纲」预填本话标题与梗概；故事页可见前情摘要与未回收伏笔。不一次生成多话剧本。

## Done when

- [x] PRD EP2-OUTLINE-01 + EP2-CONTINUITY-01 confirmed
- [x] Parse planned outline; create_episode server prefill
- [x] Continuity API returns planned_chapters; story page panel
- [x] Screens / user-flows / status; verify create path

## Notes

- Studio「+」与总览「续写」均传占位梗概，由服务端解析大纲。
- 生成分镜仍不回写梗概。
- Verified: `tests/test_planned_outline.py` + continuity unit tests; resolve against sample appendix.
