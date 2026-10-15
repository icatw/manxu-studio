import { api, toApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { aspectRatioFromApi, shotLabelToType, shotTypeToLabel } from "@/lib/domain-mappings";
import type { Character } from "@/types/character";
import type { SceneAsset } from "@/types/story";
import type { ComicProject, StoryboardPanel } from "@/types/storyboard";

export type ProjectDto = components["schemas"]["Project"];
export type EpisodeDto = components["schemas"]["Episode"];
export type CharacterDto = components["schemas"]["Character"];
export type SceneDto = components["schemas"]["Scene"];
export type PanelDto = components["schemas"]["StoryboardPanel"];
export type TaskDto = components["schemas"]["GenerationTask"];
export type WorkspaceData = {
  project: ProjectDto;
  episode: EpisodeDto;
  characters: CharacterDto[];
  scenes: SceneDto[];
  panels: PanelDto[];
  versions: Record<string, components["schemas"]["PanelImageVersion"][]>;
};

function failure(error: unknown) {
  return toApiError(error, "请求失败，请检查 API 服务后重试");
}

function required<T>(data: T | undefined, error: unknown): T {
  if (error || data === undefined) throw failure(error);
  return data;
}

export async function listProjects() {
  const { data, error } = await api.GET("/projects", { params: { query: { limit: 100 } } });
  return required(data, error).items;
}

export async function createProject(input: components["schemas"]["ProjectCreate"]) {
  const { data, error } = await api.POST("/projects", { body: input });
  return required(data, error);
}

export async function deleteProject(projectId: string) {
  const { error } = await api.DELETE("/projects/{project_id}", { params: { path: { project_id: projectId } } });
  if (error) throw failure(error);
}

export async function listEpisodes(projectId: string) {
  const { data, error } = await api.GET("/projects/{project_id}/episodes", {
    params: { path: { project_id: projectId } },
  });
  return required(data, error);
}

export async function createEpisode(projectId: string, input: components["schemas"]["EpisodeCreate"]) {
  const { data, error } = await api.POST("/projects/{project_id}/episodes", {
    params: { path: { project_id: projectId } },
    body: input,
  });
  return required(data, error);
}

export async function loadWorkspace(projectId: string, episodeId?: string): Promise<WorkspaceData> {
  const { data: projectData, error: projectError } = await api.GET("/projects/{project_id}", {
    params: { path: { project_id: projectId } },
  });
  const project = required(projectData, projectError);
  let episodes = await listEpisodes(projectId);
  if (episodes.length === 0) {
    episodes = [
      await createEpisode(projectId, { title: project.title, synopsis: project.synopsis, panel_count: 4 }),
    ];
  }
  const episode = episodes.find((item) => item.id === episodeId) ?? episodes[0];
  const [characters, scenes, panels] = await Promise.all([
    getCharacters(projectId),
    getScenes(projectId),
    getPanels(episode.id),
  ]);
  const versions = Object.fromEntries(
    await Promise.all(
      panels.map(async (panel) => [panel.id, await getPanelVersions(panel.id)] as const),
    ),
  );
  return { project, episode, characters, scenes, panels, versions };
}

async function getCharacters(projectId: string) {
  const { data, error } = await api.GET("/projects/{project_id}/characters", {
    params: { path: { project_id: projectId } },
  });
  return required(data, error);
}

async function getScenes(projectId: string) {
  const { data, error } = await api.GET("/projects/{project_id}/scenes", {
    params: { path: { project_id: projectId } },
  });
  return required(data, error);
}

async function getPanels(episodeId: string) {
  const { data, error } = await api.GET("/episodes/{episode_id}/panels", {
    params: { path: { episode_id: episodeId } },
  });
  return required(data, error);
}

async function getPanelVersions(panelId: string) {
  const { data, error } = await api.GET("/panels/{panel_id}/image-versions", {
    params: { path: { panel_id: panelId } },
  });
  return required(data, error);
}

export function toComicProject(workspace: WorkspaceData): ComicProject {
  const { project, episode, characters, scenes, panels, versions } = workspace;
  const characterAssets: Character[] = characters.map((character) => ({
    id: character.id,
    name: character.name,
    generationSource: character.profile.generation_source,
    role: character.profile.role,
    appearance: character.profile.appearance,
    hairstyle: character.profile.hairstyle,
    clothing: character.profile.outfit,
    signatureTraits: character.profile.signature_traits.join("、"),
    personality: character.profile.personality,
    imagePrompt: character.profile.image_prompt,
    referenceImageUrl: character.reference_asset_id
      ? `/api/v1/assets/${character.reference_asset_id}`
      : "",
    referenceImageSource: character.reference_asset_id ? "ai" : null,
    referenceLocked: Boolean(character.reference_locked),
    confirmed: character.status === "approved",
  }));
  const sceneAssets: SceneAsset[] = scenes.map((scene) => ({
    id: scene.id,
    name: scene.name,
    description: scene.profile.description,
    mood: [scene.profile.lighting, scene.profile.palette].filter(Boolean).join("、"),
    imageUrl: scene.reference_asset_id ? `/api/v1/assets/${scene.reference_asset_id}` : "",
    imageSource: scene.reference_asset_id ? "ai" : null,
    confirmed: scene.status === "approved",
  }));
  const panelAssets: StoryboardPanel[] = panels.map((panel, index) => {
    const currentVersion = versions[panel.id]?.find((version) => version.is_current);
    const shotType = shotLabelToType(panel.shot ?? "中景");
    return {
      id: panel.id,
      panelNumber: (panel.position ?? index) + 1,
      shotType,
      scene: panel.scene_description ?? "",
      action: panel.character_actions ?? "",
      emotion: panel.emotion ?? "",
      dialogue: panel.dialogue ?? "",
      imagePrompt: panel.image_prompt ?? "",
      composition: panel.composition ?? "",
      storyPurpose: panel.story_purpose ?? "",
      characterIds: panel.character_ids ?? [],
      sceneId: panel.scene_id ?? null,
      aspectRatio: "4:3",
      imageUrl: currentVersion?.image_url ?? null,
      imageSource: currentVersion ? "ai" : null,
      status: currentVersion ? "completed" : "draft",
      progress: currentVersion ? 100 : 0,
      errorMessage: null,
      generatedAt: currentVersion?.created_at ?? null,
      reviewStatus: panel.review_status,
    };
  });
  const panelCount = [2, 4, 6, 8, 10].includes(panelAssets.length)
    ? (panelAssets.length as ComicProject["story"]["panelCount"])
    : 4;
  return {
    id: episode.id,
    title: project.title,
    story: {
      title: episode.title,
      synopsis: episode.synopsis,
      genre: project.genre as ComicProject["story"]["genre"],
      style: project.art_style as ComicProject["story"]["style"],
      audience: "年轻成人",
      panelCount,
      aspectRatio: aspectRatioFromApi(project.aspect_ratio),
    },
    characters: characterAssets,
    scenes: sceneAssets,
    panels: panelAssets,
    updatedAt: episode.updated_at,
  };
}

export function toCharacterPatch(character: Character) {
  return {
    name: character.name,
    status: character.confirmed ? ("approved" as const) : ("draft" as const),
    reference_locked: character.referenceLocked,
    profile: {
      generation_source: character.generationSource,
      role: character.role,
      appearance: character.appearance,
      hairstyle: character.hairstyle,
      outfit: character.clothing,
      signature_traits: character.signatureTraits.split("、").filter(Boolean),
      personality: character.personality,
      visual_traits: [character.hairstyle, character.signatureTraits].filter(Boolean),
      image_prompt: character.imagePrompt,
    },
  };
}

export function toScenePatch(scene: SceneAsset) {
  return {
    name: scene.name,
    status: scene.confirmed ? ("approved" as const) : ("draft" as const),
    profile: {
      description: scene.description,
      lighting: scene.mood,
      palette: "",
      visual_traits: [],
    },
  };
}

export function toPanelPatch(panel: StoryboardPanel) {
  return {
    shot: shotTypeToLabel(panel.shotType),
    scene_description: panel.scene,
    character_actions: panel.action,
    emotion: panel.emotion,
    dialogue: panel.dialogue,
    image_prompt: panel.imagePrompt,
    character_ids: panel.characterIds,
    composition: panel.composition ?? "",
    story_purpose: panel.storyPurpose ?? "",
    scene_id: panel.sceneId ?? null,
    review_status: panel.reviewStatus ?? "draft",
  };
}

const PANEL_IMAGE_TASK_TYPES = new Set(["panel_image", "panel_image_edit"]);

/** Active panel-image tasks for an episode (newest first per API). */
export async function listActiveEpisodePanelTasks(episodeId: string): Promise<TaskDto[]> {
  const { data, error } = await api.GET("/episodes/{episode_id}/generation-tasks", {
    params: { path: { episode_id: episodeId }, query: { active_only: true } },
  });
  const tasks = required(data, error);
  return tasks.filter(
    (task) =>
      task.panel_id != null &&
      PANEL_IMAGE_TASK_TYPES.has(task.task_type) &&
      (task.status === "queued" || task.status === "running"),
  );
}

export async function waitForTask(
  taskId: string,
  onProgress?: (progress: number) => void,
  signal?: AbortSignal,
): Promise<TaskDto> {
  const delay = (milliseconds: number) => new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timeout = window.setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, milliseconds);
    const abort = () => {
      window.clearTimeout(timeout);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", abort, { once: true });
  });

  let pollDelayMs = 2000;
  while (!signal?.aborted) {
    const { data, error } = await api.GET("/generation-tasks/{task_id}", {
      params: { path: { task_id: taskId } },
      signal,
    });
    if (error) {
      const apiError = failure(error);
      if ("code" in apiError && apiError.code === "RATE_LIMITED") {
        await delay(Math.max(pollDelayMs, 5000));
        pollDelayMs = Math.min(pollDelayMs + 1000, 15000);
        continue;
      }
    }
    const task = required(data, error);
    onProgress?.(task.progress ?? 0);
    if (task.status === "succeeded") return task;
    if (task.status === "failed") {
      const error = task.error;
      const detail =
        error && typeof error === "object"
          ? "detail" in error && typeof error.detail === "string"
            ? error.detail
            : "message" in error && typeof error.message === "string"
              ? error.message
              : "title" in error && typeof error.title === "string"
                ? error.title
                : undefined
          : undefined;
      throw new Error(typeof detail === "string" ? detail : "任务失败，请重试");
    }
    if (task.status === "cancelled") throw new Error("任务已取消");
    await delay(pollDelayMs);
    pollDelayMs = Math.min(pollDelayMs + 1000, 15000);
  }
  throw new DOMException("Aborted", "AbortError");
}

export async function generateStoryAssets(
  projectId: string,
  episodeId: string,
  panelCount: number,
  options: { regenerateCharacters?: boolean } = {},
) {
  const { data, error } = await api.POST("/projects/{project_id}/story-generations", {
    params: { path: { project_id: projectId } },
    body: {
      episode_id: episodeId,
      panel_count: panelCount,
      pacing: "balanced",
      regenerate_characters: options.regenerateCharacters !== false,
      use_approved_assets: true,
      use_continuity: true,
    },
  });
  const task = await waitForTask(required(data, error).id);
  const warnings =
    task.result && "warnings" in task.result && Array.isArray(task.result.warnings)
      ? task.result.warnings.filter((warning): warning is string => typeof warning === "string")
      : [];
  return { task, warnings };
}

export async function generateSceneReferences(projectId: string) {
  const { data, error } = await api.POST("/projects/{project_id}/scene-generations", {
    params: { path: { project_id: projectId } },
    body: { image_only: true },
  });
  const task = await waitForTask(required(data, error).id);
  const result = task.result && "scene_ids" in task.result ? task.result : undefined;
  return {
    task,
    warnings: Array.isArray(result?.warnings)
      ? result.warnings.filter((warning): warning is string => typeof warning === "string")
      : [],
  };
}
