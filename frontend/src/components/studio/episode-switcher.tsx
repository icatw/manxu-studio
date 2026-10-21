import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { resolveContinueNext } from "@/lib/episode-frontier";
import { cn } from "@/lib/utils";
import { continueEpisodeGeneration, listEpisodes } from "@/services/workspace-api";
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
      const list = episodes.data ?? [];
      const decision = resolveContinueNext(list);
      if (decision.kind === "stay" || decision.kind === "studio") {
        return decision;
      }
      // SERIAL-AGENT-01: durable continue task (create only; overview can also generate storyboard).
      const result = await continueEpisodeGeneration(projectId, {
        generateStoryboard: false,
        panelCount: project.story.panelCount || 8,
      });
      return { kind: "created" as const, episodeId: result.episodeId };
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["episodes", projectId] });
      if (result.kind === "stay" || result.kind === "studio") {
        toast.message(result.toast);
        if (result.episodeId !== episodeId) {
          navigate(`/projects/${projectId}/studio?episodeId=${result.episodeId}`);
        }
        return;
      }
      navigate(`/projects/${projectId}/studio?episodeId=${result.episodeId}`);
      toast.success("已续写下一话");
    },
    onError: (error) => {
      toast.error("续写失败", { description: error instanceof Error ? error.message : undefined });
    },
  });

  return (
    <div className="flex flex-col gap-1 border-b px-2 pb-2">
      <div className="flex items-center justify-between px-2 pt-2">
        <p className="text-[11px] font-medium text-muted-foreground/80">本话</p>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="续写下一话"
          title="续写下一话（服务端建话；须先完成更早话摘要）"
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
