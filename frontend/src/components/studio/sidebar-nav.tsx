import { BookOpenText, Clapperboard, ImageIcon, LogOut, Settings, Users } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useCurrentAccount } from "@/hooks/use-current-account";
import { cn } from "@/lib/utils";
import { SHOT_TYPE_LABELS, type StudioStage } from "@/types/storyboard";
import { EpisodeSwitcher } from "./episode-switcher";
import { useStudio } from "./studio-provider";
import { StatusDot } from "./shared";

const STAGES: { id: StudioStage; label: string; icon: typeof BookOpenText }[] = [
  { id: "story", label: "故事创意", icon: BookOpenText },
  { id: "characters", label: "角色资产", icon: Users },
  { id: "scenes", label: "场景资产", icon: ImageIcon },
  { id: "storyboard", label: "分镜脚本", icon: Clapperboard },
];

export function SidebarNav() {
  const { project, stage, setStage, selectedPanelId, selectPanel, projectId } = useStudio();
  const navigate = useNavigate();
  const account = useCurrentAccount();
  const logout = useMutation({ mutationFn: async () => {
    const { error } = await api.POST("/auth/logout");
    if (error) throw new Error("登出失败");
  }, onSuccess: () => window.location.assign("/login") });
  const stageMeta: Record<StudioStage, string> = {
    story: project.story.genre,
    characters: `${project.characters.length}`,
    scenes: `${project.scenes.length}`,
    storyboard: `${project.panels.length}`,
  };

  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r bg-sidebar lg:flex" aria-label="工作流导航">
      <EpisodeSwitcher />
      <nav className="flex flex-col gap-0.5 p-2">
        <p className="px-2 pt-1 pb-2 text-[11px] font-medium text-muted-foreground/80">创作流程</p>
        {STAGES.map(({ id, label, icon: Icon }, index) => {
          const active = stage === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setStage(id)}
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
        <p className="px-4 pt-3 pb-2 text-[11px] font-medium text-muted-foreground/80">分镜列表</p>
        <ScrollArea className="min-h-0 flex-1">
          <ul className="flex flex-col gap-1 px-2 pb-2">
            {project.panels.length === 0 && (
              <li className="px-2 py-3 text-xs text-muted-foreground">暂无分镜</li>
            )}
            {project.panels.map((panel) => {
              const active = stage === "storyboard" && selectedPanelId === panel.id;
              return (
                <li key={panel.id}>
                  <button
                    type="button"
                    onClick={() => {
                      selectPanel(panel.id);
                      setStage("storyboard");
                    }}
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
                      </div>
                      <p className="truncate text-[11px] text-muted-foreground">
                        {SHOT_TYPE_LABELS[panel.shotType]} · {panel.dialogue || panel.action}
                      </p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </ScrollArea>
      </div>

      <div className="border-t p-2">
        <ButtonLink href={`/projects/${projectId}`} variant="ghost" size="sm" className="w-full justify-start text-muted-foreground">
          返回作品总览
        </ButtonLink>
        <div className="mt-2 flex items-center gap-2 border-t px-2 pt-2">
          {account.data?.avatar_url
            ? <img src={account.data.avatar_url} alt="" className="size-8 shrink-0 rounded-full object-cover" />
            : <div className="grid size-8 shrink-0 place-items-center rounded-full bg-muted text-xs">{account.data?.github_login.slice(0, 1).toUpperCase() ?? "?"}</div>}
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium">{account.data?.display_name ?? "账户"}</p>
            <p className="truncate text-[11px] text-muted-foreground">@{account.data?.github_login ?? ""}</p>
          </div>
        </div>
        <div className="mt-1 flex gap-1">
          <Button variant="ghost" size="sm" className="flex-1 justify-start text-muted-foreground" onClick={() => navigate("/settings")}><Settings />设置</Button>
          <Button variant="ghost" size="icon-sm" aria-label="退出登录" title="退出登录" disabled={logout.isPending} onClick={() => logout.mutate()}><LogOut /></Button>
        </div>
      </div>
    </aside>
  );
}
