import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type RefObject,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { usePanelGeneration, type PanelGeneration } from "@/hooks/use-panel-generation";
import {
  comparable,
  expectNoError,
  useStudioAutosave,
  useStudioHydrate,
  type SaveState,
} from "@/hooks/use-studio-persist";
import { historyReducer, createHistory, type ProjectAction } from "@/lib/project-store";
import { api, toApiError } from "@/lib/api/client";
import { waitForGenerationTask } from "@/lib/generation-task";
import { imageGenerationService, isAbortError } from "@/services/image-generation-service";
import {
  generateCharacterAssets,
  generateStoryAssets,
  listActiveEpisodeStoryTasks,
  toComicProject,
  type WorkspaceData,
} from "@/services/workspace-api";
import type { ComicProject, StoryboardPanel, StudioStage } from "@/types/storyboard";

export type { SaveState };

interface StudioContextValue {
  project: ComicProject;
  dispatch: Dispatch<ProjectAction>;
  canUndo: boolean;
  canRedo: boolean;
  undo: () => void;
  redo: () => void;
  saveState: SaveState;
  lastSavedAt: Date | null;
  stage: StudioStage;
  setStage: (stage: StudioStage) => void;
  selectedPanelId: string | null;
  selectPanel: (id: string | null) => void;
  storyBusy: boolean;
  generateFromStory: (options?: {
    regenerateCharacters?: boolean;
    characterCastMode?: "append" | "replace";
    sceneCastMode?: "append" | "replace";
  }) => Promise<void>;
  appendProjectCharacters: () => Promise<void>;
  generation: PanelGeneration;
  isAnyGenerating: boolean;
  previewOpen: boolean;
  setPreviewOpen: (open: boolean) => void;
  projectId: string;
  episodeId: string;
  refreshWorkspace: () => Promise<unknown>;
  versions: WorkspaceData["versions"];
  selectImageVersion: (panelId: string, versionId: string) => Promise<void>;
  addPanel: () => void;
  removePanel: (panelId: string) => void;
}

const StudioContext = createContext<StudioContextValue | null>(null);

export function useStudio() {
  const context = useContext(StudioContext);
  if (!context) throw new Error("useStudio must be used inside <StudioProvider>");
  return context;
}

export function StudioProvider({
  children,
  workspace,
  onReload,
}: {
  children: ReactNode;
  workspace: WorkspaceData;
  onReload: () => Promise<unknown>;
}) {
  const queryClient = useQueryClient();
  const initialProject = toComicProject(workspace);
  const [history, dispatch] = useReducer(historyReducer, initialProject, createHistory);
  const project = history.present;
  const projectRef = useRef(project) as RefObject<ComicProject>;
  projectRef.current = project;
  const baselineRef = useRef(initialProject);
  const lastSignatureRef = useRef(comparable(initialProject));
  const [stage, setStage] = useState<StudioStage>(initialProject.panels.length ? "storyboard" : "story");
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(initialProject.panels[0]?.id ?? null);
  const [storyBusy, setStoryBusy] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const storyAbortRef = useRef<AbortController | null>(null);

  const { saveState, setSaveState, lastSavedAt, setLastSavedAt } = useStudioAutosave({
    project,
    projectId: workspace.project.id,
    episodeId: workspace.episode.id,
    initialSavedAt: workspace.episode.updated_at,
    baselineRef,
    lastSignatureRef,
  });

  const modelConfig = useQuery({
    queryKey: ["model-config"],
    queryFn: async () => {
      const { data, error } = await api.GET("/model-config");
      if (error || !data) throw toApiError(error, "无法读取模型配置");
      return data;
    },
    staleTime: 60_000,
  });
  const generation = usePanelGeneration({
    projectRef,
    episodeId: workspace.episode.id,
    dispatch,
    service: imageGenerationService,
    concurrency: Math.max(1, modelConfig.data?.image_concurrency ?? 2),
    onGenerated: () => void queryClient.invalidateQueries({ queryKey: ["workspace", workspace.project.id] }),
  });

  useStudioHydrate({
    workspace,
    projectRef,
    getBusyPanelIds: generation.busyPanelIds,
    dispatch,
    setSelectedPanelId,
    setSaveState,
    setLastSavedAt,
    baselineRef,
    lastSignatureRef,
  });

  const isAnyGenerating = project.panels.some((panel) => panel.status === "generating");

  const undo = useCallback(() => {
    if (isAnyGenerating) return;
    dispatch({ type: "undo" });
  }, [isAnyGenerating]);
  const redo = useCallback(() => {
    if (isAnyGenerating) return;
    dispatch({ type: "redo" });
  }, [isAnyGenerating]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "z") return;
      event.preventDefault();
      if (event.shiftKey) redo();
      else undo();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo]);

  const applyStoryTaskSuccess = useCallback(
    async (warnings: string[], regenerateCharacters: boolean, resumed: boolean) => {
      await queryClient.invalidateQueries({ queryKey: ["workspace", workspace.project.id] });
      await onReload();
      setStage(regenerateCharacters ? "characters" : "storyboard");
      if (warnings.length) {
        toast.warning(resumed ? "后台生成已完成" : "AI 文字设定已生成", {
          description: warnings.join(" "),
        });
      } else if (resumed) {
        toast.success("本话生成已完成", { description: "切走期间任务已在后台跑完，结果已刷新。" });
      } else if (regenerateCharacters) {
        toast.success("AI 角色、场景与分镜草稿已生成", { description: "结果已保存，可继续编辑。" });
      } else {
        toast.success("本话分镜已生成", { description: "已复用作品角色库；结果已保存。" });
      }
    },
    [onReload, queryClient, workspace.project.id],
  );

  // Remounting StudioProvider on episode switch clears local storyBusy; resume server-owned pipeline tasks.
  useEffect(() => {
    const controller = new AbortController();
    storyAbortRef.current = controller;
    void (async () => {
      try {
        const active = (await listActiveEpisodeStoryTasks(workspace.episode.id))[0];
        if (!active || controller.signal.aborted) return;
        setStoryBusy(true);
        const task = await waitForGenerationTask(queryClient, active.id, { signal: controller.signal });
        if (controller.signal.aborted) return;
        const warnings =
          task.result && "warnings" in task.result && Array.isArray(task.result.warnings)
            ? task.result.warnings.filter((warning): warning is string => typeof warning === "string")
            : [];
        // Pipeline result only fills character_ids when the character stage ran.
        const regenerateCharacters = Boolean(
          task.result &&
            "character_ids" in task.result &&
            Array.isArray(task.result.character_ids) &&
            task.result.character_ids.length > 0,
        );
        await applyStoryTaskSuccess(warnings, regenerateCharacters, true);
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) return;
        toast.error("分镜生成失败", {
          description: error instanceof Error ? error.message : "请稍后重试",
        });
      } finally {
        if (!controller.signal.aborted) setStoryBusy(false);
      }
    })();
    return () => {
      controller.abort();
      if (storyAbortRef.current === controller) storyAbortRef.current = null;
    };
  }, [applyStoryTaskSuccess, queryClient, workspace.episode.id]);

  const generateFromStory = useCallback(
    async ({
      regenerateCharacters = true,
      characterCastMode = "append",
      sceneCastMode = "append",
    }: {
      regenerateCharacters?: boolean;
      characterCastMode?: "append" | "replace";
      sceneCastMode?: "append" | "replace";
    } = {}) => {
      if (!project.story.synopsis.trim()) {
        toast.error("请先填写故事梗概");
        setStage("story");
        return;
      }
      const signal = storyAbortRef.current?.signal;
      setStoryBusy(true);
      try {
        const { warnings } = await generateStoryAssets(
          workspace.project.id,
          workspace.episode.id,
          project.story.panelCount,
          { regenerateCharacters, characterCastMode, sceneCastMode, signal },
        );
        if (signal?.aborted) return;
        await applyStoryTaskSuccess(warnings, regenerateCharacters, false);
      } catch (error) {
        if (isAbortError(error) || signal?.aborted) return;
        toast.error("分镜生成失败", { description: error instanceof Error ? error.message : "请稍后重试" });
      } finally {
        if (!signal?.aborted) setStoryBusy(false);
      }
    },
    [
      applyStoryTaskSuccess,
      project.story.panelCount,
      project.story.synopsis,
      workspace.episode.id,
      workspace.project.id,
    ],
  );

  const appendProjectCharacters = useCallback(async () => {
    if (!project.story.synopsis.trim()) {
      toast.error("请先填写故事梗概");
      setStage("story");
      return;
    }
    const signal = storyAbortRef.current?.signal;
    setStoryBusy(true);
    try {
      const { task, warnings } = await generateCharacterAssets(workspace.project.id, {
        castMode: "append",
        guidance: `本话梗概：${project.story.synopsis}`,
      });
      if (signal?.aborted) return;
      await queryClient.invalidateQueries({ queryKey: ["workspace", workspace.project.id] });
      await onReload();
      setStage("characters");
      const resultIds =
        task.result && "character_ids" in task.result && Array.isArray(task.result.character_ids)
          ? task.result.character_ids
          : [];
      const added = resultIds.length;
      if (warnings.length) {
        toast.warning("角色补充完成", { description: warnings.join(" ") });
      } else if (added > 0) {
        toast.success(`已追加 ${added} 名角色`, { description: "只会新增，不会改已有定妆。" });
      } else {
        toast.success("未发现需追加的新人", { description: "作品角色库保持不变。" });
      }
    } catch (error) {
      if (isAbortError(error) || signal?.aborted) return;
      toast.error("补充角色失败", { description: error instanceof Error ? error.message : "请稍后重试" });
    } finally {
      if (!signal?.aborted) setStoryBusy(false);
    }
  }, [onReload, project.story.synopsis, queryClient, workspace.project.id]);

  const selectImageVersion = useCallback(async (panelId: string, versionId: string) => {
    const { data, error } = await api.PUT("/panels/{panel_id}/image-versions/{version_id}/selection", {
      params: { path: { panel_id: panelId, version_id: versionId } },
    });
    await expectNoError(error, data);
    if (!data) return;
    dispatch({
      type: "panelGenerated",
      id: panelId,
      patch: { imageUrl: data.image_url, status: "completed", progress: 100, imageSource: "ai" },
    });
    await queryClient.invalidateQueries({ queryKey: ["workspace", workspace.project.id] });
  }, [queryClient, workspace.project.id]);

  const addPanel = useCallback(() => {
    const panel: StoryboardPanel = {
      id: crypto.randomUUID(),
      panelNumber: projectRef.current.panels.length + 1,
      shotType: "medium",
      scene: "",
      action: "",
      emotion: "",
      dialogue: "",
      imagePrompt: "",
      characterIds: [],
      aspectRatio: projectRef.current.story.aspectRatio === "1:1" ? "1:1" : "4:3",
      imageUrl: null,
      imageSource: null,
      status: "draft",
      progress: 0,
      errorMessage: null,
      generatedAt: null,
      reviewStatus: "draft",
    };
    dispatch({ type: "setPanels", panels: [...projectRef.current.panels, panel] });
    setSelectedPanelId(panel.id);
    setStage("storyboard");
  }, [dispatch]);

  const removePanel = useCallback((panelId: string) => {
    dispatch({
      type: "setPanels",
      panels: projectRef.current.panels.filter((panel) => panel.id !== panelId),
    });
    setSelectedPanelId((current) => (current === panelId ? null : current));
  }, [dispatch]);

  useEffect(() => {
    if (selectedPanelId && !project.panels.some((panel) => panel.id === selectedPanelId)) {
      setSelectedPanelId(project.panels[0]?.id ?? null);
    }
  }, [project.panels, selectedPanelId]);

  const value = useMemo<StudioContextValue>(
    () => ({
      project,
      dispatch,
      canUndo: history.past.length > 0 && !isAnyGenerating,
      canRedo: history.future.length > 0 && !isAnyGenerating,
      undo,
      redo,
      saveState,
      lastSavedAt,
      stage,
      setStage,
      selectedPanelId,
      selectPanel: setSelectedPanelId,
      storyBusy,
      generateFromStory,
      appendProjectCharacters,
      generation,
      isAnyGenerating,
      previewOpen,
      setPreviewOpen,
      projectId: workspace.project.id,
      episodeId: workspace.episode.id,
      refreshWorkspace: onReload,
      versions: workspace.versions,
      selectImageVersion,
      addPanel,
      removePanel,
    }),
    [
      project,
      history.past.length,
      history.future.length,
      undo,
      redo,
      saveState,
      lastSavedAt,
      stage,
      selectedPanelId,
      storyBusy,
      generateFromStory,
      appendProjectCharacters,
      generation,
      isAnyGenerating,
      previewOpen,
      workspace,
      onReload,
      selectImageVersion,
      addPanel,
      removePanel,
    ],
  );

  return <StudioContext.Provider value={value}>{children}</StudioContext.Provider>;
}
