# 0030 变更影响面：IMPACT-CAST / IMPACT-BIBLE

## Goal

作者改角色视觉或作品设定集后，**知道伤到哪些已出图格**；不静默重生成，作者自行决定重绘。

## Requirements

- PRD：`IMPACT-CAST` / `IMPACT-BIBLE`（`confirmed`）
- 契约：`docs/api/openapi.yaml` — `ChangeImpact`；`PATCH` 角色/作品返回 `CharacterUpdateResult` / `ProjectUpdateResult`
- 发现来源：`0029` B01/B02

## Scope

**做**

- 服务端在视觉相关 PATCH 后计算影响摘要（已出图格数 + 涉及话）
- 工作室 / 总览软提示（toast + 可关闭横幅）
- 单测 / playground 契约对齐

**不做**

- 面板 dirty 列 / 持久 stale 标志
- 自动重绘队列
- EP2 continuity 可见（B03）、DRAFT-RESUME、F09
- PUBLISH-02；生产解冻

## Design

| 触发 | reason | 计数范围 |
| --- | --- | --- |
| 角色 profile 视觉字段变更 | `cast_visual` | 挂该角色且有 `current_image_asset_id` 的格 |
| `style_rules` / `negative_prompt` / `art_style` / `style_seed` | `bible_visual` | 作品内全部已出图格 |
| 仅 `world_setting` | `bible_continuity` | panel_count=0；仍返回 changed_fields |
| 其它字段 | `impact: null` | — |

## Acceptance

见 PRD IMPACT 验收 1–5。

## Progress

- [x] PRD / user-flows 升格
- [x] OpenAPI 包装响应
- [x] 后端 impact 查询 + 服务/路由（`change_impact.py`；PATCH 返回 UpdateResult）
- [x] 生成 `schema.d.ts`；FE toast/横幅（工作室 + 设定集）
- [x] 单测：`tests/test_change_impact.py`；FE `change-impact.test.ts`；playground bible unwrap 已改
- [ ] 手验：改角色外观 / 改画风规则 → toast + 横幅；仅改世界观 → continuity toast
- [ ] 手验通过后本计划 → completed
