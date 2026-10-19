import type { components } from "@/lib/api/schema";

export type ChangeImpact = components["schemas"]["ChangeImpact"];

export function describeChangeImpact(impact: ChangeImpact): { title: string; description: string } {
  if (impact.reason === "bible_continuity") {
    return {
      title: "世界观已更新",
      description: "续写与分镜将使用新设定；已出图不会自动重绘。",
    };
  }

  const summaries = impact.affected_episode_summaries ?? [];
  const epLabels = summaries
    .slice(0, 3)
    .map((item) => `第${item.position + 1}话`)
    .join("、");
  const more = summaries.length > 3 ? "等" : "";
  const where = epLabels ? `（${epLabels}${more}）` : "";

  if (impact.reason === "cast_visual") {
    if (impact.affected_panel_count <= 0) {
      return {
        title: "角色外观已更新",
        description: "当前没有已出图的相关画格。",
      };
    }
    return {
      title: `${impact.affected_panel_count} 格画面可能过时`,
      description: `已挂该角色的出图${where}仍基于旧设定；不会自动重绘，请按需重画。`,
    };
  }

  if (impact.affected_panel_count <= 0) {
    return {
      title: "画风设定已更新",
      description: "当前没有已出图的画格。",
    };
  }
  return {
    title: `${impact.affected_panel_count} 格画面可能过时`,
    description: `本作品已出图${where}仍基于旧画风设定；不会自动重绘，请按需重画。`,
  };
}

export function mergeChangeImpacts(impacts: ChangeImpact[]): ChangeImpact | null {
  const meaningful = impacts.filter(
    (item) => item.reason === "bible_continuity" || item.affected_panel_count > 0,
  );
  if (meaningful.length === 0) return null;
  // Prefer the strongest visual hit for the banner; toast can fire per impact.
  return (
    meaningful.find((item) => item.reason === "cast_visual" && item.affected_panel_count > 0) ??
    meaningful.find((item) => item.reason === "bible_visual" && item.affected_panel_count > 0) ??
    meaningful[0] ??
    null
  );
}
