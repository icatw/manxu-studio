import { api, toApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

function required<T>(data: T | undefined, error: unknown): T {
  if (error || data === undefined) throw toApiError(error, "请求失败");
  return data;
}

export type ProjectPlanDraft = components["schemas"]["ProjectPlanDraft"];
export type ProjectPlanRequest = components["schemas"]["ProjectPlanRequest"];
export type PlotThread = components["schemas"]["PlotThread"];
export type EpisodeReader = components["schemas"]["EpisodeReader"];
export type ProjectContinuity = components["schemas"]["ProjectContinuity"];

export async function getProjectContinuity(
  projectId: string,
  options?: { beforePosition?: number },
) {
  const { data, error } = await api.GET("/projects/{project_id}/continuity", {
    params: {
      path: { project_id: projectId },
      query: {
        before_position: options?.beforePosition,
      },
    },
  });
  return required(data, error);
}

export async function planProject(body: ProjectPlanRequest) {
  const { data, error } = await api.POST("/projects/plan", { body });
  return required(data, error);
}

export async function createProjectFromPlan(body: components["schemas"]["ProjectFromPlanCreate"]) {
  const { data, error } = await api.POST("/projects/from-plan", { body });
  return required(data, error);
}

export async function listPlotThreads(projectId: string) {
  const { data, error } = await api.GET("/projects/{project_id}/plot-threads", {
    params: { path: { project_id: projectId } },
  });
  return required(data, error);
}

export async function createPlotThread(
  projectId: string,
  body: components["schemas"]["PlotThreadCreate"],
) {
  const { data, error } = await api.POST("/projects/{project_id}/plot-threads", {
    params: { path: { project_id: projectId } },
    body,
  });
  return required(data, error);
}

export async function updatePlotThread(
  threadId: string,
  body: components["schemas"]["PlotThreadPatch"],
) {
  const { data, error } = await api.PATCH("/plot-threads/{thread_id}", {
    params: { path: { thread_id: threadId } },
    body,
  });
  return required(data, error);
}

export async function deletePlotThread(threadId: string) {
  const { error } = await api.DELETE("/plot-threads/{thread_id}", {
    params: { path: { thread_id: threadId } },
  });
  if (error) throw toApiError(error, "删除伏笔失败");
}

export async function generateEpisodeSummary(episodeId: string) {
  const { data, error } = await api.POST("/episodes/{episode_id}/summary", {
    params: { path: { episode_id: episodeId } },
  });
  return required(data, error);
}

export async function getEpisodeReader(episodeId: string) {
  const { data, error } = await api.GET("/episodes/{episode_id}/reader", {
    params: { path: { episode_id: episodeId } },
  });
  return required(data, error);
}

export async function updateProjectBible(
  projectId: string,
  body: components["schemas"]["ProjectPatch"],
) {
  const { data, error } = await api.PATCH("/projects/{project_id}", {
    params: { path: { project_id: projectId } },
    body,
  });
  return required(data, error);
}
