import { BookOpenText, Clapperboard, ImageIcon, Users } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useEpisodeLayoutLettering } from "@/hooks/use-episode-layout-lettering";
import { letteringSummary } from "@/lib/lettering-summary";
import { cn } from "@/lib/utils";
import { SHOT_TYPE_LABELS, type StudioStage } from "@/types/storyboard";
import { EpisodeSwitcher } from "./episode-switcher";
import { useStudio } from "./studio-provider";
import { StatusDot } from "./shared";

const STAGES: { id: StudioStage; label: string; hint: string; icon: typeof BookOpenText }[] = [
  { id: "story", label: "故事创意", hint: "本话", icon: BookOpenText },
  { id: "characters", label: "作品角色", hint: "全话共用", icon: Users },
  { id: "scenes", label: "作品场景", hint: "全话共用", icon: ImageIcon },
  { id: "storyboard", label: "分镜脚本", hint: "本话", icon: Clapperboard },
];

export function SidebarNav() {
  const { project, stage, setStage, selectedPanelId, selectPanel, episodeId } = useStudio();
  const lettering = useEpisodeLayoutLettering(episodeId);
  const stageMeta: Record<StudioStage, string> = {
    story: project.story.genre,
    characters: `${project.characters.length}`,
    scenes: `${project.scenes.length}`,
    storyboard: `${project.panels.length}`,
  };

  return (
    <aside className="hidden h-full min-h-0 w-56 shrink-0 flex-col border-r bg-sidebar lg:flex" aria-label="工作流导航">
      <EpisodeSwitcher />
      <nav className="flex flex-col gap-0.5 p-2">
        <p className="px-2 pt-1 pb-2 text-[11px] font-medium text-muted-foreground/80">创作流程</p>
        {STAGES.map(({ id, label, hint, icon: Icon }, index) => {
          const active = stage === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setStage(id)}
              title={`${label}（${hint}）`}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex h-9 items-center gap-2.5 rounded-md px-2 text-left text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded text-[10px] font-semibold tabular-nums",
                  active ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                )}
                aria-hidden
              >
                {index + 1}
              </span>
              <Icon className="size-4 shrink-0" aria-hidden />
              <span className="flex-1 truncate">{label}</span>
              <span className="text-[11px] text-muted-foreground tabular-nums">{stageMeta[id]}</span>
            </button>
          );
        })}
      </nav>

      <div className="mx-3 h-px bg-border" aria-hidden />
      <div className="flex min-h-0 flex-1 flex-col">
        {stage !== "storyboard" ? (
          <div className="p-2">
            <button
              type="button"
              onClick={() => setStage("storyboard")}
              className="flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground"
            >
              <span>分镜列表</span>
              <span className="tabular-nums">
                {project.panels.length} 格 · 进入
              </span>
            </button>
          </div>
        ) : (
          <>
            <p className="px-4 pt-3 pb-2 text-[11px] font-medium text-muted-foreground/80">分镜列表</p>
            <ScrollArea className="min-h-0 flex-1">
              <ul className="flex flex-col gap-1 px-2 pb-2">
                {project.panels.length === 0 && (
                  <li className="px-2 py-3 text-xs text-muted-foreground">暂无分镜</li>
                )}
                {project.panels.map((panel) => {
                  const active = selectedPanelId === panel.id;
                  const items = lettering.byPanelId.get(panel.id)?.lettering ?? [];
                  const summary = letteringSummary(items) || panel.dialogue || panel.action;
                  const fromLettering = items.length > 0 && Boolean(letteringSummary(items));
                  return (
                    <li key={panel.id}>
                      <button
                        type="button"
                        onClick={() => selectPanel(panel.id)}
                        aria-current={active ? "true" : undefined}
                        className={cn(
                          "flex w-full items-center gap-2.5 rounded-md p-1.5 text-left transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                          active ? "bg-sidebar-accent" : "hover:bg-sidebar-accent/60",
                        )}
                      >
                        <div className="relative aspect-[4/3] w-14 shrink-0 overflow-hidden rounded bg-muted">
                          {panel.imageUrl && <img src={panel.imageUrl} alt="" className="absolute inset-0 size-full object-cover" />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-medium tabular-nums">第 {panel.panelNumber} 格</span>
                            <StatusDot status={panel.status} />
                            {fromLettering ? (
                              <span className="rounded bg-muted px-1 py-px text-[10px] text-muted-foreground">
                                字效
                              </span>
                            ) : null}
                          </div>
                          <p className="truncate text-[11px] text-muted-foreground">
                            {SHOT_TYPE_LABELS[panel.shotType]} · {summary}
                          </p>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </ScrollArea>
          </>
        )}
      </div>
    </aside>
  );
}
