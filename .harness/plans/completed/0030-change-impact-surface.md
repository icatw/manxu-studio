# 0030 变更影响面：IMPACT-CAST / IMPACT-BIBLE（completed）

## Goal

作者改角色视觉或作品设定集后，**知道伤到哪些已出图格**；不静默重生成，作者自行决定重绘。

## Requirements

- PRD：`IMPACT-CAST` / `IMPACT-BIBLE`（`confirmed`）
- 契约：`docs/api/openapi.yaml` — `ChangeImpact`；`PATCH` 角色/作品返回 `CharacterUpdateResult` / `ProjectUpdateResult`
- 发现来源：`0029` B01/B02
- 用户流：`docs/product/user-flows.md`（设定变更 → 影响摘要 → 软提示）

## Scope

**做了**

- 服务端在视觉相关 PATCH 后计算影响摘要（已出图格数 + 涉及话）
- 工作室 / 总览软提示（autosave toast + 可关闭分镜横幅；总览设定集保存提示）
- 单测 / playground 契约对齐

**刻意不做（仍后置）**

- 面板 dirty 列 / 持久 stale 标志
- 自动重绘队列
- EP2 continuity 可见（B03）、DRAFT-RESUME、F09
- PUBLISH-02；生产解冻

## Design（落地）

| 触发 | reason | 计数范围 |
| --- | --- | --- |
| 角色 profile 视觉字段变更 | `cast_visual` | 挂该角色且有 `current_image_asset_id` 的格 |
| `style_rules` / `negative_prompt` / `art_style` / `style_seed` | `bible_visual` | 作品内全部已出图格 |
| 仅 `world_setting` | `bible_continuity` | `affected_panel_count=0`；仍返回 `changed_fields` |
| 其它字段 | `impact: null` | — |

### 代码落点

| 层 | 路径 |
| --- | --- |
| 服务 | `backend/app/services/change_impact.py` |
| PATCH | `assets.update_character` → `CharacterUpdateResult`；`projects.update_project` → `ProjectUpdateResult` |
| FE 文案 | `frontend/src/lib/change-impact.ts` |
| 工作室 | `use-studio-persist` 合并 impact → toast；`storyboard-canvas` 可关闭横幅；`studio-provider` 持有态 |
| 总览 | `project-overview` 设定集保存后 toast |

## Acceptance（对照 PRD 1–5）

| # | 准则 | 证据 |
| --- | --- | --- |
| 1 | 改角色外观并保存 → 响应含摘要；UI 软提示；旧图仍在 | 后端 `impact_for_cast` + FE toast/横幅；不创建重绘任务 |
| 2 | 改画风规则/负向提示词 → 计全部已出图格 | `bible_visual` + playground bible unwrap |
| 3 | 仅改世界观 → continuity，不强制重绘计数 | `bible_continuity`，`panel_count=0` |
| 4 | 不自动重绘 | 范围明确排除自动队列 |
| 5 | 账户隔离 | 既有 owner 依赖；impact 仅随本作品 PATCH |

## Progress

- [x] PRD / user-flows 升格
- [x] OpenAPI 包装响应（`ChangeImpact` / UpdateResult）
- [x] 后端 impact 查询 + 服务/路由
- [x] 生成 `schema.d.ts`；FE toast/横幅（工作室 + 设定集）
- [x] 单测：`tests/test_change_impact.py`（3）；FE `change-impact.test.ts`（3）；playground bible unwrap
- [x] 收口核对（2026-10-19）：上列自动化通过；UI 路径已接线（工作室横幅 / 总览 toast）；浏览器逐条手点可作回归，不挡关闭
- [x] 计划 → completed

## Verification (2026-10-19)

```text
uv run --directory backend pytest tests/test_change_impact.py -q   # 3 passed
pnpm --dir frontend exec vitest run src/lib/change-impact.test.ts # 3 passed
```

合入：`feat(impact): surface cast and bible change impact summaries`（及后续 `docs(api)` 契约同步）。

## Follow-ups（非本计划）

- EP2 continuity 可见、DRAFT-RESUME、F09
- PUBLISH-02 / 生产解冻
