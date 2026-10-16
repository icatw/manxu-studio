import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  LayoutTemplate,
  Loader2,
  MessageSquareText,
  PenLine,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toApiError } from "@/lib/api/client";
import { listEpisodes } from "@/services/workspace-api";
import { LetteringOverlay } from "@/components/series/lettering-overlay";
import {
  bootstrapEpisodeLayout,
  createLetteringObject,
  deleteLetteringObject,
  getEpisodeLayout,
  getEpisodeLayoutPreview,
  reorderPageSlots,
  seedLetteringFromDialogue,
  syncEpisodeLayout,
  updateLetteringObject,
  updatePageSlot,
  type LetteringObject,
  type PageSlot,
} from "@/services/layout-api";

function layoutQueryKey(episodeId: string) {
  return ["layout", episodeId] as const;
}

function previewQueryKey(episodeId: string) {
  return ["layout-preview", episodeId] as const;
}

export function LayoutPage() {
  const { projectId = "", episodeId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [selectedLetteringId, setSelectedLetteringId] = useState<string | null>(null);

  const episodes = useQuery({
    queryKey: ["episodes", projectId],
    queryFn: () => listEpisodes(projectId),
    enabled: Boolean(projectId),
  });
  const episode = episodes.data?.find((item) => item.id === episodeId);

  const layout = useQuery({
    queryKey: layoutQueryKey(episodeId),
    queryFn: () => getEpisodeLayout(episodeId),
    enabled: Boolean(episodeId),
  });

  const preview = useQuery({
    queryKey: previewQueryKey(episodeId),
    queryFn: () => getEpisodeLayoutPreview(episodeId),
    enabled: Boolean(episodeId) && (layout.data?.pages.length ?? 0) > 0,
  });

  const imageBySlot = useMemo(() => {
    const map = new Map<string, string | null>();
    for (const item of preview.data?.items ?? []) {
      map.set(item.slot_id, item.image_url);
    }
    return map;
  }, [preview.data]);

  const invalidateLayout = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: layoutQueryKey(episodeId) }),
      queryClient.invalidateQueries({ queryKey: previewQueryKey(episodeId) }),
    ]);
  };

  const bootstrap = useMutation({
    mutationFn: () => bootstrapEpisodeLayout(episodeId),
    onSuccess: async () => {
      toast.success("已生成默认竖条页");
      await invalidateLayout();
      setMode("edit");
    },
    onError: (error) => {
      toast.error("生成布局失败", {
        description: toApiError(error, "请先在工作室为该话生成画格").message,
      });
    },
  });

  const sync = useMutation({
    mutationFn: () => syncEpisodeLayout(episodeId, { follow_current_version: true }),
    onSuccess: async () => {
      toast.success("已与分镜同步");
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("同步失败", { description: toApiError(error).message });
    },
  });

  const reorder = useMutation({
    mutationFn: ({ pageId, slotIds }: { pageId: string; slotIds: string[] }) =>
      reorderPageSlots(pageId, slotIds),
    onSuccess: async () => {
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("调整顺序失败", { description: toApiError(error).message });
    },
  });

  const patchSlot = useMutation({
    mutationFn: ({ slotId, body }: { slotId: string; body: Parameters<typeof updatePageSlot>[1] }) =>
      updatePageSlot(slotId, body),
    onSuccess: async () => {
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("保存槽位失败", { description: toApiError(error).message });
    },
  });

  const seedLettering = useMutation({
    mutationFn: (replaceExisting: boolean) =>
      seedLetteringFromDialogue(episodeId, { replace_existing: replaceExisting }),
    onSuccess: async () => {
      toast.success("已从分镜对白生成气泡");
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("生成气泡失败", { description: toApiError(error).message });
    },
  });

  const createLettering = useMutation({
    mutationFn: ({
      slotId,
      body,
    }: {
      slotId: string;
      body: Parameters<typeof createLetteringObject>[1];
    }) => createLetteringObject(slotId, body),
    onSuccess: async (row) => {
      setSelectedLetteringId(row.id);
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("添加字效失败", { description: toApiError(error).message });
    },
  });

  const patchLettering = useMutation({
    mutationFn: ({
      letteringId,
      body,
    }: {
      letteringId: string;
      body: Parameters<typeof updateLetteringObject>[1];
    }) => updateLetteringObject(letteringId, body),
    onSuccess: async () => {
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("保存字效失败", { description: toApiError(error).message });
    },
  });

  const removeLettering = useMutation({
    mutationFn: (letteringId: string) => deleteLetteringObject(letteringId),
    onSuccess: async () => {
      setSelectedLetteringId(null);
      await invalidateLayout();
    },
    onError: (error) => {
      toast.error("删除字效失败", { description: toApiError(error).message });
    },
  });

  if (layout.isPending || episodes.isPending) {
    return (
      <main className="grid min-h-dvh place-items-center text-sm text-muted-foreground">
        正在打开成稿排版…
      </main>
    );
  }

  if (layout.isError || !layout.data) {
    return (
      <main className="grid min-h-dvh place-items-center p-6 text-center">
        <div>
          <h1 className="text-base font-semibold">无法打开成稿排版</h1>
          <ButtonLink href={`/projects/${projectId}`} className="mt-4">
            返回作品
          </ButtonLink>
        </div>
      </main>
    );
  }

  const pages = layout.data.pages;
  const hasLayout = pages.length > 0;
  const flatSlots = pages.flatMap((page) =>
    page.slots.map((slot) => ({ page, slot })),
  );
  const busy =
    bootstrap.isPending ||
    sync.isPending ||
    reorder.isPending ||
    patchSlot.isPending ||
    seedLettering.isPending ||
    createLettering.isPending ||
    patchLettering.isPending ||
    removeLettering.isPending;

  const selectedSlot =
    flatSlots.find(({ slot }) => slot.id === selectedSlotId)?.slot ??
    flatSlots[0]?.slot ??
    null;
  const selectedLettering: LetteringObject | null =
    (selectedSlot?.lettering ?? []).find((item) => item.id === selectedLetteringId) ?? null;

  const moveSlot = (pageId: string, slots: PageSlot[], index: number, delta: number) => {
    const next = index + delta;
    if (next < 0 || next >= slots.length) return;
    const ids = slots.map((slot) => slot.id);
    const tmp = ids[index]!;
    ids[index] = ids[next]!;
    ids[next] = tmp;
    reorder.mutate({ pageId, slotIds: ids });
  };

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4">
          <button
            type="button"
            className="flex min-w-0 items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            onClick={() => navigate(`/projects/${projectId}`)}
          >
            <ChevronLeft className="size-4 shrink-0" aria-hidden />
            <span className="truncate">作品</span>
          </button>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              成稿排版 · {episode?.title ?? "本话"}
            </p>
            <p className="truncate text-xs text-muted-foreground">竖条漫 · 与工作室制作态区分</p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <Button
              size="sm"
              variant={mode === "edit" ? "default" : "outline"}
              disabled={!hasLayout}
              onClick={() => setMode("edit")}
            >
              编辑
            </Button>
            <Button
              size="sm"
              variant={mode === "preview" ? "default" : "outline"}
              disabled={!hasLayout}
              onClick={() => setMode("preview")}
            >
              成稿预览
            </Button>
            <ButtonLink
              href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
              variant="outline"
              size="sm"
            >
              <PenLine data-icon="inline-start" />
              工作室
            </ButtonLink>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        {!hasLayout ? (
          <section className="mx-auto flex max-w-lg flex-col items-center gap-4 rounded-xl border px-6 py-16 text-center">
            <LayoutTemplate className="size-10 text-muted-foreground" aria-hidden />
            <h1 className="text-lg font-semibold">尚未生成竖条页</h1>
            <p className="text-sm text-muted-foreground">
              将按当前分镜顺序创建默认竖条布局（一格一槽）。需本话已有画格。
            </p>
            <Button onClick={() => bootstrap.mutate()} disabled={busy}>
              {bootstrap.isPending ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Sparkles data-icon="inline-start" />
              )}
              生成默认竖条页
            </Button>
            <ButtonLink
              href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
              variant="ghost"
              size="sm"
            >
              先去工作室出图
            </ButtonLink>
          </section>
        ) : mode === "preview" ? (
          <section className="mx-auto max-w-xl">
            <p className="mb-4 text-center text-xs text-muted-foreground">
              成稿预览 · 含字效叠层 · 非制作预览导出
            </p>
            <ol className="flex flex-col">
              {(preview.data?.items ??
                flatSlots.map(({ slot }) => ({
                  slot_id: slot.id,
                  height_px: slot.height_px,
                  gap_after_px: slot.gap_after_px,
                  image_url: imageBySlot.get(slot.id) ?? null,
                  panel_id: slot.panel_id,
                  page_id: slot.page_id,
                  lettering: slot.lettering ?? [],
                }))).map((item, index) => (
                <li
                  key={item.slot_id}
                  className="relative flex flex-col overflow-hidden"
                  style={{ marginBottom: item.gap_after_px }}
                >
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={`第 ${index + 1} 格`}
                      className="w-full rounded-sm bg-muted object-cover"
                      style={{ height: item.height_px }}
                    />
                  ) : (
                    <div
                      className="flex w-full items-center justify-center rounded-sm bg-muted px-4 text-center text-sm text-muted-foreground"
                      style={{ height: item.height_px }}
                    >
                      画面未就绪 · 回工作室出图
                    </div>
                  )}
                  <LetteringOverlay items={item.lettering ?? []} />
                </li>
              ))}
            </ol>
          </section>
        ) : (
          <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
            <div className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy}
                  onClick={() => sync.mutate()}
                >
                  {sync.isPending ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <RefreshCw data-icon="inline-start" />
                  )}
                  同步分镜
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy}
                  onClick={() => seedLettering.mutate(false)}
                >
                  {seedLettering.isPending ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <MessageSquareText data-icon="inline-start" />
                  )}
                  从分镜生成气泡
                </Button>
                <span className="text-xs text-muted-foreground">
                  重绘保布局与字效；生成气泡默认不覆盖已有字效
                </span>
              </div>
              <ol className="flex flex-col gap-4">
                {flatSlots.map(({ page, slot }, index) => {
                  const imageUrl = imageBySlot.get(slot.id) ?? null;
                  const siblings = page.slots;
                  const localIndex = siblings.findIndex((item) => item.id === slot.id);
                  const active = selectedSlot?.id === slot.id;
                  return (
                    <li
                      key={slot.id}
                      className={`overflow-hidden rounded-xl border bg-card ${active ? "ring-2 ring-primary" : ""}`}
                    >
                      <div className="flex items-center justify-between gap-2 border-b px-3 py-2 text-xs text-muted-foreground">
                        <button
                          type="button"
                          className="tabular-nums hover:text-foreground"
                          onClick={() => {
                            setSelectedSlotId(slot.id);
                            setSelectedLetteringId(slot.lettering?.[0]?.id ?? null);
                          }}
                        >
                          格 {index + 1}
                          {(slot.lettering?.length ?? 0) > 0
                            ? ` · ${slot.lettering!.length} 字效`
                            : ""}
                        </button>
                        <div className="flex items-center gap-1">
                          <Button
                            size="icon-sm"
                            variant="ghost"
                            disabled={busy || localIndex <= 0}
                            aria-label="上移"
                            onClick={() => moveSlot(page.id, siblings, localIndex, -1)}
                          >
                            <ArrowUp />
                          </Button>
                          <Button
                            size="icon-sm"
                            variant="ghost"
                            disabled={busy || localIndex >= siblings.length - 1}
                            aria-label="下移"
                            onClick={() => moveSlot(page.id, siblings, localIndex, 1)}
                          >
                            <ArrowDown />
                          </Button>
                        </div>
                      </div>
                      <div
                        className="relative"
                        onClick={() => {
                          setSelectedSlotId(slot.id);
                          setSelectedLetteringId(slot.lettering?.[0]?.id ?? null);
                        }}
                      >
                        {imageUrl ? (
                          <img
                            src={imageUrl}
                            alt={`第 ${index + 1} 格`}
                            className="w-full bg-muted object-cover"
                            style={{ height: slot.height_px }}
                          />
                        ) : (
                          <div
                            className="flex w-full items-center justify-center bg-muted px-4 text-center text-sm text-muted-foreground"
                            style={{ height: slot.height_px }}
                          >
                            缺图占位
                            <ButtonLink
                              href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
                              variant="link"
                              size="sm"
                              className="ml-2"
                            >
                              去出图
                            </ButtonLink>
                          </div>
                        )}
                        <LetteringOverlay
                          items={slot.lettering ?? []}
                          interactive
                          selectedId={selectedLetteringId}
                          onSelect={(id) => {
                            setSelectedSlotId(slot.id);
                            setSelectedLetteringId(id);
                          }}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3 border-t p-3">
                        <label className="grid gap-1 text-xs">
                          <span className="text-muted-foreground">格高 (px)</span>
                          <Input
                            type="number"
                            min={80}
                            max={4096}
                            defaultValue={slot.height_px}
                            key={`${slot.id}-h-${slot.height_px}`}
                            disabled={busy}
                            onBlur={(event) => {
                              const value = Number(event.target.value);
                              if (!Number.isFinite(value) || value === slot.height_px) return;
                              patchSlot.mutate({
                                slotId: slot.id,
                                body: { height_px: value },
                              });
                            }}
                          />
                        </label>
                        <label className="grid gap-1 text-xs">
                          <span className="text-muted-foreground">下间距 (px)</span>
                          <Input
                            type="number"
                            min={0}
                            max={512}
                            defaultValue={slot.gap_after_px}
                            key={`${slot.id}-g-${slot.gap_after_px}`}
                            disabled={busy}
                            onBlur={(event) => {
                              const value = Number(event.target.value);
                              if (!Number.isFinite(value) || value === slot.gap_after_px) return;
                              patchSlot.mutate({
                                slotId: slot.id,
                                body: { gap_after_px: value },
                              });
                            }}
                          />
                        </label>
                      </div>
                    </li>
                  );
                })}
              </ol>
            </div>
            <aside className="h-fit space-y-4 rounded-xl border p-4 text-sm lg:sticky lg:top-20">
              <div>
                <h2 className="font-medium">字效</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  选中格后编辑气泡/旁白。改字不重绘底图。
                </p>
              </div>
              {selectedSlot ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      onClick={() =>
                        createLettering.mutate({
                          slotId: selectedSlot.id,
                          body: {
                            kind: "speech_bubble",
                            text: "对白",
                            x_pct: 8,
                            y_pct: 6,
                            width_pct: 60,
                            tail: "bottom_left",
                            font_size: "md",
                          },
                        })
                      }
                    >
                      <Plus data-icon="inline-start" />
                      气泡
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      onClick={() =>
                        createLettering.mutate({
                          slotId: selectedSlot.id,
                          body: {
                            kind: "narration",
                            text: "旁白",
                            y_pct: 78,
                            width_pct: 84,
                            x_pct: 8,
                            tail: "none",
                            font_size: "md",
                          },
                        })
                      }
                    >
                      <Plus data-icon="inline-start" />
                      旁白
                    </Button>
                  </div>
                  <ul className="flex flex-col gap-1">
                    {(selectedSlot.lettering ?? []).map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          className={`w-full truncate rounded-md px-2 py-1.5 text-left text-xs ${
                            selectedLetteringId === item.id
                              ? "bg-sidebar-accent"
                              : "hover:bg-muted/60"
                          }`}
                          onClick={() => setSelectedLetteringId(item.id)}
                        >
                          {item.kind === "speech_bubble" ? "气泡" : "旁白"} · {item.text}
                        </button>
                      </li>
                    ))}
                    {(selectedSlot.lettering ?? []).length === 0 ? (
                      <li className="text-xs text-muted-foreground">本格尚无字效</li>
                    ) : null}
                  </ul>
                  {selectedLettering ? (
                    <div className="space-y-2 border-t pt-3">
                      <label className="grid gap-1 text-xs">
                        <span className="text-muted-foreground">文案</span>
                        <Textarea
                          key={`${selectedLettering.id}-text`}
                          defaultValue={selectedLettering.text}
                          rows={3}
                          disabled={busy}
                          onBlur={(event) => {
                            const value = event.target.value.trim();
                            if (!value || value === selectedLettering.text) return;
                            patchLettering.mutate({
                              letteringId: selectedLettering.id,
                              body: { text: value },
                            });
                          }}
                        />
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {(
                          [
                            ["x_pct", "X%"],
                            ["y_pct", "Y%"],
                            ["width_pct", "宽%"],
                          ] as const
                        ).map(([field, label]) => (
                          <label key={field} className="grid gap-1 text-xs">
                            <span className="text-muted-foreground">{label}</span>
                            <Input
                              type="number"
                              min={field === "width_pct" ? 10 : 0}
                              max={100}
                              defaultValue={selectedLettering[field]}
                              key={`${selectedLettering.id}-${field}-${selectedLettering[field]}`}
                              disabled={busy}
                              onBlur={(event) => {
                                const value = Number(event.target.value);
                                if (!Number.isFinite(value) || value === selectedLettering[field]) {
                                  return;
                                }
                                patchLettering.mutate({
                                  letteringId: selectedLettering.id,
                                  body: { [field]: value },
                                });
                              }}
                            />
                          </label>
                        ))}
                      </div>
                      <label className="grid gap-1 text-xs">
                        <span className="text-muted-foreground">字号</span>
                        <select
                          className="h-8 rounded-md border bg-background px-2"
                          value={selectedLettering.font_size}
                          disabled={busy}
                          onChange={(event) =>
                            patchLettering.mutate({
                              letteringId: selectedLettering.id,
                              body: {
                                font_size: event.target.value as LetteringObject["font_size"],
                              },
                            })
                          }
                        >
                          <option value="sm">小</option>
                          <option value="md">中</option>
                          <option value="lg">大</option>
                        </select>
                      </label>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        disabled={busy}
                        onClick={() => removeLettering.mutate(selectedLettering.id)}
                      >
                        <Trash2 data-icon="inline-start" />
                        删除字效
                      </Button>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">先选中一格。</p>
              )}
              <Button
                className="w-full"
                variant="outline"
                size="sm"
                onClick={() => setMode("preview")}
              >
                查看成稿预览
              </Button>
            </aside>
          </section>
        )}
      </main>
    </div>
  );
}
