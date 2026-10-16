import { api, toApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

function required<T>(data: T | undefined, error: unknown): T {
  if (error || data === undefined) throw toApiError(error, "请求失败");
  return data;
}

export type EpisodeLayout = components["schemas"]["EpisodeLayout"];
export type LayoutPage = components["schemas"]["LayoutPage"];
export type PageSlot = components["schemas"]["PageSlot"];
export type LayoutPreview = components["schemas"]["LayoutPreview"];
export type BootstrapLayoutRequest = components["schemas"]["BootstrapLayoutRequest"];
export type PageSlotPatch = components["schemas"]["PageSlotPatch"];

export async function getEpisodeLayout(episodeId: string) {
  const { data, error } = await api.GET("/episodes/{episode_id}/layout", {
    params: { path: { episode_id: episodeId } },
  });
  return required(data, error);
}

export async function bootstrapEpisodeLayout(
  episodeId: string,
  body?: BootstrapLayoutRequest,
) {
  const { data, error } = await api.POST("/episodes/{episode_id}/layout/bootstrap", {
    params: { path: { episode_id: episodeId } },
    ...(body ? { body } : {}),
  });
  return required(data, error);
}

export async function syncEpisodeLayout(
  episodeId: string,
  body?: components["schemas"]["SyncLayoutRequest"],
) {
  const { data, error } = await api.POST("/episodes/{episode_id}/layout/sync", {
    params: { path: { episode_id: episodeId } },
    ...(body ? { body } : {}),
  });
  return required(data, error);
}

export async function getEpisodeLayoutPreview(episodeId: string) {
  const { data, error } = await api.GET("/episodes/{episode_id}/layout/preview", {
    params: { path: { episode_id: episodeId } },
  });
  return required(data, error);
}

export async function reorderPageSlots(pageId: string, slotIds: string[]) {
  const { data, error } = await api.PUT("/pages/{page_id}/slots/order", {
    params: { path: { page_id: pageId } },
    body: { slot_ids: slotIds },
  });
  return required(data, error);
}

export async function updatePageSlot(slotId: string, body: PageSlotPatch) {
  const { data, error } = await api.PATCH("/slots/{slot_id}", {
    params: { path: { slot_id: slotId } },
    body,
  });
  return required(data, error);
}
