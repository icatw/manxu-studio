import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { createEpisode, listEpisodes } from "@/services/workspace-api";
import { useStudio } from "./studio-provider";

export function EpisodeSwitcher() {
  const { projectId, episodeId, project } = useStudio();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const episodes = useQuery({
    queryKey: ["episodes", projectId],
    queryFn: () => listEpisodes(projectId),
  });

  const create = useMutation({
    mutationFn: async () => {
      const nextNumber = (episodes.data?.length ?? 0) + 1;
      return createEpisode(projectId, {
        title: `第 ${nextNumber} 话`,
        synopsis: project.story.synopsis || "待补充本话梗概",
        panel_count: project.story.panelCount || 8,
      });
    },
    onSuccess: async (episode) => {
      await queryClient.invalidateQueries({ queryKey: ["episodes", projectId] });
      navigate(`/projects/${projectId}/studio?episodeId=${episode.id}`);
      toast.success(`已新建${episode.title}`);
    },
    onError: (error) => {
      toast.error("新建失败", { description: error instanceof Error ? error.message : undefined });
    },
  });

  return (
    <div className="flex flex-col gap-1 border-b px-2 pb-2">
      <div className="flex items-center justify-between px-2 pt-2">
        <p className="text-[11px] font-medium text-muted-foreground/80">本话</p>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="新建下一话"
          title="新建下一话"
          disabled={create.isPending || episodes.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
        </Button>
      </div>
      {episodes.isPending ? (
        <p className="px-2 py-2 text-xs text-muted-foreground">加载中…</p>
      ) : episodes.isError ? (
        <p className="px-2 py-2 text-xs text-destructive">无法加载话列表</p>
      ) : (
        <ScrollArea className="max-h-36">
          <ul className="flex flex-col gap-0.5" aria-label="话列表">
            {(episodes.data ?? []).map((episode, index) => {
              const active = episode.id === episodeId;
              return (
                <li key={episode.id}>
                  <button
                    type="button"
                    aria-current={active ? "true" : undefined}
                    onClick={() => {
                      if (!active) navigate(`/projects/${projectId}/studio?episodeId=${episode.id}`);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                    )}
                  >
                    <span className="tabular-nums text-muted-foreground">#{index + 1}</span>
                    <span className="min-w-0 flex-1 truncate font-medium">{episode.title}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </ScrollArea>
      )}
    </div>
  );
}
