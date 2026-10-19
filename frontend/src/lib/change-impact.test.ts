import { describe, expect, it } from "vitest";
import { describeChangeImpact, mergeChangeImpacts, type ChangeImpact } from "./change-impact";

const castHit: ChangeImpact = {
  reason: "cast_visual",
  changed_fields: ["appearance"],
  affected_panel_count: 3,
  affected_episode_ids: ["e1"],
  affected_episode_summaries: [{ episode_id: "e1", position: 0, title: "第1话", panel_count: 3 }],
};

describe("describeChangeImpact", () => {
  it("summarizes cast visual hits", () => {
    const copy = describeChangeImpact(castHit);
    expect(copy.title).toContain("3 格");
    expect(copy.description).toContain("不会自动重绘");
  });

  it("explains continuity-only bible edits", () => {
    const copy = describeChangeImpact({
      reason: "bible_continuity",
      changed_fields: ["world_setting"],
      affected_panel_count: 0,
      affected_episode_ids: [],
    });
    expect(copy.title).toContain("世界观");
  });
});

describe("mergeChangeImpacts", () => {
  it("prefers cast visual for the banner", () => {
    const merged = mergeChangeImpacts([
      {
        reason: "bible_continuity",
        changed_fields: ["world_setting"],
        affected_panel_count: 0,
        affected_episode_ids: [],
      },
      castHit,
    ]);
    expect(merged?.reason).toBe("cast_visual");
  });
});
