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
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { usePanelGeneration, type PanelGeneration } from "@/hooks/use-panel-generation";
import { historyReducer, createHistory, type ProjectAction } from "@/lib/project-store";
import { api } from "@/lib/api/client";
import { createImageGenerationService } from "@/services/image-generation-service";
import {
  generateStoryAssets,
  toCharacterPatch,
  toPanelPatch,
  toScenePatch,
  toComicProject,
  type WorkspaceData,
} from "@/services/workspace-api";
import type { ComicProject, StoryboardPanel, StudioStage } from "@/types/storyboard";

export type SaveState = "idle" | "saving" | "saved" | "error";

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
  generateFromStory: (options?: { regenerateCharacters?: boolean }) => Promise<void>;
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

function comparable(project: ComicProject) {
  return JSON.stringify({
    title: project.title,
    story: project.story,
    characters: project.characters.map(toCharacterPatch),
    scenes: project.scenes.map(toScenePatch),
    panels: project.panels.map((panel) => ({ id: panel.id, ...toPanelPatch(panel) })),
  });
}

async function expectNoError(error: unknown, data?: unknown) {
  if (error || data === undefined) {
    const detail =
      typeof error === "object" && error !== null && "detail" in error
        ? String((error as { detail: unknown }).detail)
        : "API 保存失败，请检查服务后重试";
    throw new Error(detail);
  }
}

async function persistProject(
  current: ComicProject,
  previous: ComicProject,
  projectId: string,
  episodeId: string,
) {
  const projectPatch: Record<string, string> = {};
  if (current.title !== previous.title) projectPatch.title = current.title;
  if (current.story.synopsis !== previous.story.synopsis) projectPatch.synopsis = current.story.synopsis;
  if (current.story.genre !== previous.story.genre) projectPatch.genre = current.story.genre;
  if (current.story.style !== previous.story.style) projectPatch.art_style = current.story.style;
  const aspectRatio = current.story.aspectRatio ?? "16:9";
  const previousAspectRatio = previous.story.aspectRatio ?? "16:9";
  if (aspectRatio !== previousAspectRatio) {
    projectPatch.aspect_ratio = aspectRatio === "1:1" ? "square" : aspectRatio === "3:4" ? "portrait" : "landscape";
  }
  if (Object.keys(projectPatch).length) {
    const { data, error } = await api.PATCH("/projects/{project_id}", {
      params: { path: { project_id: projectId } },
      body: projectPatch,
    });
    await expectNoError(error, data);
  }

  const episodePatch: Record<string, string | number> = {};
  if (current.story.title !== previous.story.title) episodePatch.title = current.story.title;
  if (current.story.synopsis !== previous.story.synopsis) episodePatch.synopsis = current.story.synopsis;
  if (current.story.panelCount !== previous.story.panelCount) episodePatch.panel_count = current.story.panelCount;
  if (Object.keys(episodePatch).length) {
    const { data, error } = await api.PATCH("/episodes/{episode_id}", {
      params: { path: { episode_id: episodeId } },
      body: episodePatch,
    });
    await expectNoError(error, data);
  }

  const previousCharacters = new Map(previous.characters.map((item) => [item.id, item]));
  for (const character of current.characters) {
    const before = previousCharacters.get(character.id);
    if (!before || JSON.stringify(toCharacterPatch(before)) === JSON.stringify(toCharacterPatch(character))) continue;
    const { data, error } = await api.PATCH("/characters/{character_id}", {
      params: { path: { character_id: character.id } },
      body: toCharacterPatch(character),
    });
    await expectNoError(error, data);
  }

  const previousScenes = new Map(previous.scenes.map((item) => [item.id, item]));
  for (const scene of current.scenes) {
    const before = previousScenes.get(scene.id);
    if (!before || JSON.stringify(toScenePatch(before)) === JSON.stringify(toScenePatch(scene))) continue;
    const { data, error } = await api.PATCH("/scenes/{scene_id}", {
      params: { path: { scene_id: scene.id } },
      body: toScenePatch(scene),
    });
    await expectNoError(error, data);
  }

  const previousPanels = new Map(previous.panels.map((item) => [item.id, item]));
  const currentPanels = new Map(current.panels.map((item) => [item.id, item]));
  for (const panel of previous.panels) {
    if (currentPanels.has(panel.id)) continue;
    const { error } = await api.DELETE("/panels/{panel_id}", { params: { path: { panel_id: panel.id } } });
    if (error) throw new Error("删除分镜失败，请重试");
  }
  for (const panel of current.panels) {
    const before = previousPanels.get(panel.id);
    if (!before) {
      const { data, error } = await api.POST("/episodes/{episode_id}/panels", {
        params: { path: { episode_id: episodeId } },
        body: { id: panel.id, ...toPanelPatch(panel) },
      });
      await expectNoError(error, data);
      continue;
    }
    if (JSON.stringify(toPanelPatch(before)) === JSON.stringify(toPanelPatch(panel))) continue;
    const { data, error } = await api.PATCH("/panels/{panel_id}", {
      params: { path: { panel_id: panel.id } },
      body: toPanelPatch(panel),
    });
    await expectNoError(error, data);
  }
  const previousOrder = previous.panels.map((panel) => panel.id);
  const currentOrder = current.panels.map((panel) => panel.id);
  if (currentOrder.length && JSON.stringify(previousOrder) !== JSON.stringify(currentOrder)) {
    const { data, error } = await api.PUT("/episodes/{episode_id}/panels/order", {
      params: { path: { episode_id: episodeId } },
      body: { panel_ids: currentOrder },
    });
    await expectNoError(error, data);
  }
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
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(new Date(workspace.episode.updated_at));
  const [stage, setStage] = useState<StudioStage>(initialProject.panels.length ? "storyboard" : "story");
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(initialProject.panels[0]?.id ?? null);
  const [storyBusy, setStoryBusy] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const lastSignatureRef = useRef(comparable(initialProject));
  const workspaceSignature = JSON.stringify(workspace);
  const workspaceSignatureRef = useRef(workspaceSignature);

  const imageService = useMemo(
    () => createImageGenerationService({ provider: "server", model: "", negativePrompt: "" }),
    [],
  );
  const generation = usePanelGeneration({
    projectRef,
    dispatch,
    service: imageService,
    onGenerated: () => void queryClient.invalidateQueries({ queryKey: ["workspace", workspace.project.id] }),
  });
  const isAnyGenerating = project.panels.some((panel) => panel.status === "generating");

  useEffect(() => {
    setReady(true);
  }, []);

  useEffect(() => {
    if (workspaceSignature === workspaceSignatureRef.current) return;
    workspaceSignatureRef.current = workspaceSignature;
    const next = toComicProject(workspace);
    baselineRef.current = next;
    lastSignatureRef.current = comparable(next);
    dispatch({ type: "hydrate", project: next });
    setSelectedPanelId(next.panels[0]?.id ?? null);
    setSaveState("saved");
    setLastSavedAt(new Date(workspace.episode.updated_at));
  }, [workspace, workspaceSignature]);

  useEffect(() => {
    if (!ready) return;
    const signature = comparable(project);
    if (signature === lastSignatureRef.current) return;
    setSaveState("saving");
    const timer = window.setTimeout(async () => {
      try {
        await persistProject(project, baselineRef.current, workspace.project.id, workspace.episode.id);
        baselineRef.current = structuredClone(project);
        lastSignatureRef.current = signature;
        setSaveState("saved");
        setLastSavedAt(new Date());
      } catch (error) {
        setSaveState("error");
        toast.error("保存失败", { description: error instanceof Error ? error.message : "请检查网络后重试" });
      }
    }, 650);
    return () => window.clearTimeout(timer);
  }, [project, ready, workspace.episode.id, workspace.project.id]);

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

  const generateFromStory = useCallback(
    async ({ regenerateCharacters = true }: { regenerateCharacters?: boolean } = {}) => {
      if (!project.story.synopsis.trim()) {
        toast.error("请先填写故事梗概");
        setStage("story");
        return;
      }
      setStoryBusy(true);
      try {
        const { warnings } = await generateStoryAssets(workspace.project.id, workspace.episode.id, project.story.panelCount, {
          regenerateCharacters,
        });
        await queryClient.invalidateQueries({ queryKey: ["workspace", workspace.project.id] });
        await onReload();
        setStage(regenerateCharacters ? "characters" : "storyboard");
        if (warnings.length) {
          toast.warning("AI 文字设定已生成", {
            description: warnings.filter((warning): warning is string => typeof warning === "string").join(" "),
          });
        } else {
          toast.success("AI 角色、场景与分镜草稿已生成", { description: "结果已保存，可继续编辑。" });
        }
      } catch (error) {
        toast.error("分镜生成失败", { description: error instanceof Error ? error.message : "请稍后重试" });
      } finally {
        setStoryBusy(false);
      }
    },
    [onReload, project.story.panelCount, project.story.synopsis, queryClient, workspace.episode.id, workspace.project.id],
  );

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
