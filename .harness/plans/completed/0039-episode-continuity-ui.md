# 0039 — 话间 continuity 注入对齐 + 续写入口一致 + F09

## Goal

修「完整漫画」多话流程三处摩擦：生成注入按当前话过滤前情；工作室「+」与总览「续写」同一 frontier；有字效时画布卡弱化场景描述。

## Done when

- [x] 分镜/流水线注入的前情仅含 `position < 当前话` 的摘要（与故事页展示一致）
- [x] OpenAPI `GET continuity` 可选 `before_position`；故事页用该参数
- [x] 工作室侧栏「+」复用总览 frontier（先摘要 / 打开空壳 / 再新建）
- [x] F09：有 Lettering 时画布卡不再堆完整场景长文
- [x] 单测 + 相关前端测；status 更新

## Notes

- 需求依据：SERIAL-03、EP2-CONTINUITY-01（已 confirmed）；F09 为 A′ deferred 打磨，本轮顺手收。
- 不实现 DRAFT-RESUME / PUBLISH-02。
- Verified: `pytest tests/test_serial_continuity.py` + storyboard flush test；`episode-frontier.test.ts`；frontend typecheck。
