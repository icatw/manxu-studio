"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { toast } from "sonner";
import { toApiError } from "@/lib/api/client";
import {
  bootstrapEpisodeLayout,
  createLetteringObject,
  deleteLetteringObject,
  getEpisodeLayout,
  seedLetteringFromDialogue,
  updateLetteringObject,
  type LetteringObject,
  type LetteringObjectCreate,
  type LetteringObjectPatch,
} from "@/services/layout-api";

export function layoutQueryKey(episodeId: string) {
  return ["layout", episodeId] as const;
}

export type PanelLetteringBinding = {
  slotId: string;
  lettering: LetteringObject[];
};

export function useEpisodeLayoutLettering(episodeId: string | undefined) {
  const queryClient = useQueryClient();
  const enabled = Boolean(episodeId);

  const layout = useQuery({
    queryKey: episodeId ? layoutQueryKey(episodeId) : ["layout", "none"],
    queryFn: () => getEpisodeLayout(episodeId!),
    enabled,
  });

  const byPanelId = useMemo(() => {
    const map = new Map<string, PanelLetteringBinding>();
    for (const page of layout.data?.pages ?? []) {
      for (const slot of page.slots) {
        map.set(slot.panel_id, {
          slotId: slot.id,
          lettering: slot.lettering ?? [],
        });
      }
    }
    return map;
  }, [layout.data]);

  const hasPages = (layout.data?.pages.length ?? 0) > 0;

  const invalidate = async () => {
    if (!episodeId) return;
    await queryClient.invalidateQueries({ queryKey: layoutQueryKey(episodeId) });
    await queryClient.invalidateQueries({ queryKey: ["layout-preview", episodeId] });
  };

  const ensureLayout = async () => {
    if (!episodeId) throw new Error("缺少话 ID");
    if (hasPages) return layout.data!;
    return bootstrapEpisodeLayout(episodeId);
  };

  const seed = useMutation({
    mutationFn: async (replaceExisting: boolean) => {
      if (!episodeId) throw new Error("缺少话 ID");
      await ensureLayout();
      return seedLetteringFromDialogue(episodeId, { replace_existing: replaceExisting });
    },
    onSuccess: async (_data, replaceExisting) => {
      toast.success(replaceExisting ? "已用分镜对白替换并重新生成气泡" : "已从分镜对白生成气泡");
      await invalidate();
    },
    onError: (error) => {
      toast.error("生成气泡失败", { description: toApiError(error).message });
    },
  });

  const create = useMutation({
    mutationFn: async ({
      slotId,
      body,
    }: {
      slotId: string;
      body: LetteringObjectCreate;
    }) => createLetteringObject(slotId, body),
    onSuccess: async () => {
      await invalidate();
    },
    onError: (error) => {
      toast.error("添加字效失败", { description: toApiError(error).message });
    },
  });

  const patch = useMutation({
    mutationFn: async ({
      letteringId,
      body,
    }: {
      letteringId: string;
      body: LetteringObjectPatch;
    }) => updateLetteringObject(letteringId, body),
    onSuccess: async () => {
      await invalidate();
    },
    onError: (error) => {
      toast.error("更新字效失败", { description: toApiError(error).message });
    },
  });

  const remove = useMutation({
    mutationFn: async (letteringId: string) => deleteLetteringObject(letteringId),
    onSuccess: async () => {
      await invalidate();
    },
    onError: (error) => {
      toast.error("删除字效失败", { description: toApiError(error).message });
    },
  });

  return {
    layout,
    byPanelId,
    hasPages,
    busy:
      layout.isFetching ||
      seed.isPending ||
      create.isPending ||
      patch.isPending ||
      remove.isPending,
    invalidate,
    seed,
    create,
    patch,
    remove,
  };
}
