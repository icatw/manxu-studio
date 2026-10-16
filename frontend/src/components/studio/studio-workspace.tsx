import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { TooltipProvider } from "@/components/ui/tooltip";
import { loadWorkspace } from "@/services/workspace-api";
import { CharacterBoard } from "./character-board";
import { ComicPreviewDialog } from "./comic-preview-dialog";
import { PanelInspector } from "./panel-inspector";
import { SceneBoard } from "./scene-board";
import { EpisodeSwitcher } from "./episode-switcher";
import { SidebarNav } from "./sidebar-nav";
import { StatusBar } from "./status-bar";
import { StoryEditor } from "./story-editor";
import { StoryboardCanvas } from "./storyboard-canvas";
import { StudioProvider, useStudio } from "./studio-provider";
import { TopToolbar } from "./top-toolbar";

function StageView() {
  const { stage } = useStudio();
  if (stage === "story") return <StoryEditor />;
  if (stage === "characters") return <CharacterBoard />;
  if (stage === "scenes") return <SceneBoard />;
  return <StoryboardCanvas />;
}

function WorkspaceShell() {
  const { stage, setStage } = useStudio();
  return (
    <TooltipProvider>
      <div className="flex h-dvh max-h-dvh min-h-0 min-w-0 flex-col overflow-hidden">
        <TopToolbar />
        <div className="border-b bg-sidebar lg:hidden">
          <EpisodeSwitcher />
        </div>
        <nav className="flex shrink-0 gap-1 overflow-x-auto border-b bg-sidebar p-2 lg:hidden" aria-label="创作流程">
          {(["story", "characters", "scenes", "storyboard"] as const).map((item, index) => (
            <button
              key={item}
              type="button"
              aria-current={stage === item ? "step" : undefined}
              onClick={() => setStage(item)}
              className={`shrink-0 rounded-md px-3 py-2 text-xs ${stage === item ? "bg-sidebar-accent text-foreground" : "text-muted-foreground"}`}
            >
              {index + 1}. {item === "story" ? "故事" : item === "characters" ? "角色" : item === "scenes" ? "场景" : "分镜"}
            </button>
          ))}
        </nav>
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden max-lg:flex-col">
          <SidebarNav />
          <main className="canvas-dots min-h-0 min-w-0 flex-1 overflow-y-auto">
            <StageView />
          </main>
          <PanelInspector />
        </div>
        <StatusBar />
        <ComicPreviewDialog />
      </div>
    </TooltipProvider>
  );
}

const STUDIO_STAGES = new Set(["story", "characters", "scenes", "storyboard"]);

export function StudioWorkspace({ projectId }: { projectId: string }) {
  const [searchParams] = useSearchParams();
  const episodeId = searchParams.get("episodeId") ?? undefined;
  const stageParam = searchParams.get("stage");
  const initialStage =
    stageParam && STUDIO_STAGES.has(stageParam)
      ? (stageParam as "story" | "characters" | "scenes" | "storyboard")
      : undefined;
  const workspaceQuery = useQuery({
    queryKey: ["workspace", projectId, episodeId ?? "first"],
    queryFn: () => loadWorkspace(projectId, episodeId),
  });

  if (workspaceQuery.isPending) {
    return <main className="grid min-h-dvh place-items-center text-sm text-muted-foreground">正在打开项目…</main>;
  }
  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <main className="grid min-h-dvh place-items-center p-6 text-center">
        <div>
          <h1 className="text-base font-semibold">无法打开项目</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {workspaceQuery.error instanceof Error ? workspaceQuery.error.message : "项目不存在或 API 服务不可用"}
          </p>
          <button className="mt-4 text-sm text-primary underline" onClick={() => void workspaceQuery.refetch()}>
            重新加载
          </button>
        </div>
      </main>
    );
  }

  return (
    <StudioProvider
      key={`${projectId}:${workspaceQuery.data.episode.id}:${initialStage ?? "default"}`}
      workspace={workspaceQuery.data}
      onReload={() => workspaceQuery.refetch()}
      initialStage={initialStage}
    >
      <WorkspaceShell />
    </StudioProvider>
  );
}
