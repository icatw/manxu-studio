import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronLeft,
  Download,
  FileImage,
  Files,
  LayoutTemplate,
  Loader2,
  MessageSquareText,
  PenLine,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { AccountMenu } from "@/components/account-menu";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { Input } from "@/components/ui/input";
import { api, toApiError } from "@/lib/api/client";
import { waitForGenerationTask } from "@/lib/generation-task";
import { queryClient as sharedQueryClient } from "@/lib/query-client";
import { cn } from "@/lib/utils";
import { listEpisodes } from "@/services/workspace-api";
import { LetteringOverlay } from "@/components/series/lettering-overlay";
import {
  bootstrapEpisodeLayout,
  getEpisodeLayout,
  getEpisodeLayoutPreview,
  reorderPageSlots,
  syncEpisodeLayout,
  updatePageSlot,
  type PageSlot,
} from "@/services/layout-api";

type ManuscriptFormat = "png" | "png_zip" | "pdf";

function layoutQueryKey(episodeId: string) {
  return ["layout", episodeId] as const;
}

function previewQueryKey(episodeId: string) {
  return ["layout-preview", episodeId] as const;
}

function previewSeenKey(episodeId: string) {
  return `manxu:layout-preview-seen:${episodeId}`;
}

function cleanHintKey(episodeId: string) {
  return `manxu:layout-clean-hint:${episodeId}`;
}

export function LayoutPage() {
  const { projectId = "", episodeId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<ManuscriptFormat | null>(null);
  const [previewSeen, setPreviewSeen] = useState(false);
  const [cleanHintDismissed, setCleanHintDismissed] = useState(false);
  const exportMenuId = useId();
  const exportWrapRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!exportOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!exportWrapRef.current?.contains(event.target as Node)) setExportOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExportOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [exportOpen]);

  useEffect(() => {
    if (!episodeId) return;
    try {
      setPreviewSeen(sessionStorage.getItem(previewSeenKey(episodeId)) === "1");
      setCleanHintDismissed(sessionStorage.getItem(cleanHintKey(episodeId)) === "1");
    } catch {
      setPreviewSeen(false);
      setCleanHintDismissed(false);
    }
  }, [episodeId]);

  useEffect(() => {
    if (mode !== "preview" || !episodeId) return;
    setPreviewSeen(true);
    try {
      sessionStorage.setItem(previewSeenKey(episodeId), "1");
    } catch {
      /* ignore */
    }
  }, [mode, episodeId]);

  const handleManuscriptExport = async (format: ManuscriptFormat) => {
    if (!episodeId) return;
    setExportOpen(false);
    setExportingFormat(format);
    try {
      const { data, error } = await api.POST("/episodes/{episode_id}/manuscript-exports", {
        params: { path: { episode_id: episodeId } },
        body: { format },
      });
      if (error || !data) throw toApiError(error, "无法创建成稿导出任务");
      const task = await waitForGenerationTask(sharedQueryClient, data.id);
      const result = task.result;
      if (!result || !("download_url" in result)) throw new Error("成稿导出未返回下载地址");
      const response = await fetch(result.download_url, { credentials: "include" });
      if (!response.ok) throw new Error("下载成稿失败");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      const disposition = response.headers.get("content-disposition") ?? "";
      const utf8Name = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1];
      const asciiName = /filename="([^"]+)"/i.exec(disposition)?.[1];
      const fromHeader = utf8Name ? decodeURIComponent(utf8Name) : asciiName;
      const base =
        (episode?.title || "成稿").replace(/[\\/:*?"<>|]+/g, "_").trim() || "成稿";
      const fallback =
        format === "png"
          ? `${base}-成稿.png`
          : format === "png_zip"
            ? `${base}-成稿.zip`
            : `${base}-成稿.pdf`;
      const preferred = fromHeader || fallback;
      anchor.download = preferred.match(/\.(png|zip|pdf)$/i) ? preferred : fallback;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success(
        format === "png"
          ? "成稿长图已导出"
          : format === "png_zip"
            ? "成稿分页 ZIP 已导出"
            : "成稿 PDF 已导出",
      );
    } catch (error) {
      toast.error("成稿导出失败", {
        description: error instanceof Error ? error.message : toApiError(error).message,
      });
    } finally {
      setExportingFormat(null);
    }
  };

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
    bootstrap.isPending || sync.isPending || reorder.isPending || patchSlot.isPending;

  const selectedSlot =
    flatSlots.find(({ slot }) => slot.id === selectedSlotId)?.slot ??
    flatSlots[0]?.slot ??
    null;

  const stripItems =
    preview.data?.items ??
    flatSlots.map(({ slot }) => ({
      slot_id: slot.id,
      image_url: imageBySlot.get(slot.id) ?? null,
      lettering: slot.lettering ?? [],
    }));
  const missingImageCount = stripItems.filter((item) => !item.image_url).length;
  const missingLetteringCount = stripItems.filter(
    (item) => (item.lettering?.length ?? 0) === 0,
  ).length;
  const showCleanHints =
    hasLayout && !cleanHintDismissed && (missingImageCount > 0 || missingLetteringCount > 0);
  const showPreviewBeforeExport = hasLayout && !previewSeen && mode === "edit";

  const dismissCleanHints = () => {
    setCleanHintDismissed(true);
    if (!episodeId) return;
    try {
      sessionStorage.setItem(cleanHintKey(episodeId), "1");
    } catch {
      /* ignore */
    }
  };

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
            <span className="truncate">作品总览</span>
          </button>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              成稿排版 · {episode?.title ?? "本话"}
            </p>
            <p className="truncate text-xs text-muted-foreground">竖条漫成稿 · 非制作预览</p>
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
              title="成稿预览：只读竖条（含字效）· 非制作预览"
              onClick={() => setMode("preview")}
            >
              成稿预览
            </Button>
            <div className="relative" ref={exportWrapRef}>
              <Button
                size="sm"
                variant="outline"
                aria-label="导出成稿"
                aria-haspopup="menu"
                aria-expanded={exportOpen}
                aria-controls={exportMenuId}
                title="导出成稿（长图 / 分页 ZIP / PDF）· 非制作导出"
                disabled={!hasLayout || exportingFormat !== null}
                onClick={() => setExportOpen((open) => !open)}
              >
                {exportingFormat !== null ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : (
                  <Download data-icon="inline-start" />
                )}
                <span className="hidden sm:inline">导出成稿</span>
                <ChevronDown
                  className={cn("hidden size-3.5 sm:inline", exportOpen && "rotate-180")}
                  aria-hidden
                />
              </Button>
              {exportOpen ? (
                <div
                  id={exportMenuId}
                  role="menu"
                  aria-label="成稿导出格式"
                  className="absolute right-0 z-40 mt-1 w-56 rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
                >
                  <p className="px-2 py-1.5 text-[11px] text-muted-foreground">
                    成稿导出 · 按竖条页 + 字效 · 非制作导出
                  </p>
                  {(
                    [
                      {
                        format: "png" as const,
                        label: "成稿长图 PNG",
                        description: "全部槽位连成一条竖图",
                        icon: Download,
                      },
                      {
                        format: "png_zip" as const,
                        label: "成稿分页 ZIP",
                        description: "按成稿页切成多张 PNG",
                        icon: Files,
                      },
                      {
                        format: "pdf" as const,
                        label: "成稿 PDF",
                        description: "按成稿页合成 PDF",
                        icon: FileImage,
                      },
                    ] as const
                  ).map((item) => (
                    <button
                      key={item.format}
                      type="button"
                      role="menuitem"
                      className="flex w-full items-start gap-2 rounded-sm px-2 py-2 text-left text-sm hover:bg-accent disabled:opacity-50"
                      disabled={exportingFormat !== null}
                      onClick={() => {
                        void handleManuscriptExport(item.format);
                      }}
                    >
                      <item.icon
                        className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                        aria-hidden
                      />
                      <span className="min-w-0">
                        <span className="block font-medium">{item.label}</span>
                        <span className="block text-xs text-muted-foreground">
                          {item.description}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <ButtonLink
              href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
              variant="outline"
              size="sm"
            >
              <PenLine data-icon="inline-start" />
              工作室
            </ButtonLink>
            <AccountMenu />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        {showCleanHints || showPreviewBeforeExport ? (
          <div className="mb-4 space-y-2">
            {showCleanHints ? (
              <div
                role="status"
                className="flex flex-wrap items-start gap-2 rounded-lg border bg-muted/30 px-3 py-2 text-xs text-muted-foreground"
              >
                <div className="min-w-0 flex-1 space-y-1 text-pretty">
                  {missingImageCount > 0 ? (
                    <p>
                      {missingImageCount} 格画面未就绪 ·{" "}
                      <ButtonLink
                        href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
                        variant="link"
                        size="sm"
                        className="h-auto px-0 text-xs"
                      >
                        回工作室出图
                      </ButtonLink>
                    </p>
                  ) : null}
                  {missingLetteringCount > 0 ? (
                    <p>
                      {missingLetteringCount} 格尚无字效 · 成稿导出不会印分镜对白 ·{" "}
                      <ButtonLink
                        href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
                        variant="link"
                        size="sm"
                        className="h-auto px-0 text-xs"
                      >
                        回工作室制作预览种泡
                      </ButtonLink>
                    </p>
                  ) : null}
                </div>
                <Button
                  size="icon-xs"
                  variant="ghost"
                  aria-label="关闭清洁提示"
                  onClick={dismissCleanHints}
                >
                  <X />
                </Button>
              </div>
            ) : null}
            {showPreviewBeforeExport ? (
              <div
                role="status"
                className="flex flex-wrap items-center gap-2 rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground"
              >
                <p className="min-w-0 flex-1 text-pretty">
                  建议先打开<strong className="font-medium text-foreground">成稿预览</strong>
                  确认竖条与字效，再「导出成稿」。
                </p>
                <Button size="xs" variant="secondary" onClick={() => setMode("preview")}>
                  成稿预览
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
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
              成稿预览 · 含字效叠层 · 非制作预览 · 非制作导出
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
                <span className="text-xs text-muted-foreground">
                  本页调槽序与间距；字效请在工作室「制作预览」编辑
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
                          onClick={() => setSelectedSlotId(slot.id)}
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
                        onClick={() => setSelectedSlotId(slot.id)}
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
                            className="flex w-full flex-wrap items-center justify-center gap-2 bg-muted px-4 text-center text-sm text-muted-foreground"
                            style={{ height: slot.height_px }}
                          >
                            <span>画面未就绪 · 回工作室出图</span>
                            <ButtonLink
                              href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
                              variant="link"
                              size="sm"
                            >
                              去出图
                            </ButtonLink>
                          </div>
                        )}
                        <LetteringOverlay items={slot.lettering ?? []} />
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
                <h2 className="font-medium">页结构</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  调整槽序、格高与间距。字效真源在槽上，主编辑在工作室制作预览。
                </p>
              </div>
              {selectedSlot ? (
                <p className="text-xs text-muted-foreground">
                  格已选中 · {(selectedSlot.lettering ?? []).length} 个字效（只读叠层）
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">选中一格可调下方格高/间距。</p>
              )}
              <ButtonLink
                href={`/projects/${projectId}/studio?episodeId=${episodeId}`}
                variant="outline"
                size="sm"
                className="w-full"
              >
                <MessageSquareText data-icon="inline-start" />
                回工作室改字效
              </ButtonLink>
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
