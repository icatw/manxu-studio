import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ArrowLeft, BookOpen, ChevronDown, Files, LayoutTemplate, Loader2, PenLine, Plus, ScrollText, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { AccountMenu } from "@/components/account-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, toApiError } from "@/lib/api/client";
import { waitForGenerationTask } from "@/lib/generation-task";
import { queryClient as appQueryClient } from "@/lib/query-client";
import {
  createEpisode,
  deleteProject,
  listCharacters,
  listEpisodes,
  type CharacterDto,
} from "@/services/workspace-api";
import {
  createPlotThread,
  deletePlotThread,
  generateEpisodeSummary,
  listPlotThreads,
  updatePlotThread,
  updateProjectBible,
  type PlotThread,
} from "@/services/serial-api";
import { cn } from "@/lib/utils";

type Tab = "chapters" | "cast" | "bible" | "threads";

export function ProjectOverview() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("chapters");
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: async () => {
      const { data, error } = await api.GET("/projects/{project_id}", {
        params: { path: { project_id: projectId } },
      });
      if (error || !data) throw new Error("无法读取作品");
      return data;
    },
    enabled: Boolean(projectId),
  });
  const episodes = useQuery({
    queryKey: ["episodes", projectId],
    queryFn: () => listEpisodes(projectId),
    enabled: Boolean(projectId),
  });
  const threads = useQuery({
    queryKey: ["plot-threads", projectId],
    queryFn: () => listPlotThreads(projectId),
    enabled: Boolean(projectId),
  });
  const characters = useQuery({
    queryKey: ["characters", projectId],
    queryFn: () => listCharacters(projectId),
    enabled: Boolean(projectId),
  });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const remove = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => navigate("/projects"),
    onError: (error) => toast.error("删除失败", { description: error.message }),
  });

  if (project.isPending) {
    return <main className="grid min-h-dvh place-items-center text-sm text-muted-foreground">正在打开作品…</main>;
  }
  if (project.isError || !project.data) {
    return (
      <main className="grid min-h-dvh place-items-center p-6 text-center">
        <div>
          <h1 className="text-base font-semibold">无法打开作品</h1>
          <ButtonLink href="/projects" className="mt-4">返回作品库</ButtonLink>
        </div>
      </main>
    );
  }

  const detail = project.data;
  const openThreads = (threads.data ?? []).filter((thread) => !thread.resolved).length;
  const cast = characters.data ?? [];
  const approvedCast = cast.filter((item) => item.status === "approved").length;
  const lockedCast = cast.filter((item) => item.reference_locked).length;
  const firstEpisodeId = episodes.data?.[0]?.id;

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center gap-3 border-b px-5">
        <ButtonLink href="/projects" variant="ghost" size="sm">
          <ArrowLeft data-icon="inline-start" />
          作品库
        </ButtonLink>
        <span className="text-sm text-muted-foreground">/</span>
        <span className="min-w-0 flex-1 truncate text-sm font-medium">{detail.title}</span>
        <AccountMenu />
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-8 px-5 py-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <div className="relative aspect-[16/10] w-full shrink-0 overflow-hidden rounded-xl bg-muted md:w-80">
            {detail.cover_image_url ? (
              <img src={detail.cover_image_url} alt="" className="absolute inset-0 size-full object-cover" />
            ) : (
              <div className="flex size-full items-center justify-center text-4xl font-bold text-muted-foreground/40">
                {detail.title.slice(0, 2)}
              </div>
            )}
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{detail.genre}</Badge>
              <Badge variant="outline">{detail.art_style}</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">{detail.title}</h1>
            <p className="text-sm leading-relaxed text-muted-foreground">{detail.synopsis}</p>
            <dl className="flex flex-wrap gap-6 pt-1 text-sm">
              <div><dt className="text-xs text-muted-foreground">话次</dt><dd className="text-lg font-semibold tabular-nums">{episodes.data?.length ?? 0}</dd></div>
              <div><dt className="text-xs text-muted-foreground">全剧角色</dt><dd className="text-lg font-semibold tabular-nums">{cast.length}</dd></div>
              <div><dt className="text-xs text-muted-foreground">未回收伏笔</dt><dd className="text-lg font-semibold tabular-nums">{openThreads}</dd></div>
            </dl>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 border-b">
          <div role="tablist" aria-label="作品内容" className="flex gap-1">
            {([
              { id: "chapters" as const, label: "话次" },
              { id: "cast" as const, label: "角色" },
              { id: "bible" as const, label: "设定集" },
              { id: "threads" as const, label: "伏笔" },
            ]).map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={tab === item.id}
                onClick={() => setTab(item.id)}
                className={cn(
                  "-mb-px border-b-2 px-3 pb-2.5 text-sm",
                  tab === item.id ? "border-primary font-medium" : "border-transparent text-muted-foreground",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
          <Button variant="ghost" size="sm" className="mb-1.5 text-muted-foreground hover:text-destructive" disabled={remove.isPending} onClick={() => setConfirmDelete(true)}>
            <Trash2 data-icon="inline-start" />
            删除作品
          </Button>
        </div>

        {tab === "chapters" ? (
          <ChapterList
            projectId={projectId}
            projectTitle={detail.title}
            episodes={episodes.data ?? []}
            onChanged={() => {
              void queryClient.invalidateQueries({ queryKey: ["episodes", projectId] });
              void project.refetch();
            }}
          />
        ) : null}
        {tab === "cast" ? (
          <CastRoster
            projectId={projectId}
            characters={cast}
            approvedCount={approvedCast}
            lockedCount={lockedCast}
            studioHref={
              firstEpisodeId
                ? `/projects/${projectId}/studio?episodeId=${firstEpisodeId}&stage=characters`
                : `/projects/${projectId}/studio?stage=characters`
            }
            loading={characters.isPending}
            onRefresh={() => void characters.refetch()}
          />
        ) : null}
        {tab === "bible" ? (
          <BibleForm
            projectId={projectId}
            worldSetting={detail.world_setting ?? ""}
            styleRules={detail.style_rules ?? ""}
            negativePrompt={detail.negative_prompt ?? ""}
            styleSeed={detail.style_seed ?? null}
            onSaved={() => void project.refetch()}
          />
        ) : null}
        {tab === "threads" ? (
          <ThreadList
            projectId={projectId}
            threads={threads.data ?? []}
            onChanged={() => void queryClient.invalidateQueries({ queryKey: ["plot-threads", projectId] })}
          />
        ) : null}
      </main>
      {confirmDelete ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="overview-delete-title"
            aria-describedby="overview-delete-description"
            className="w-full max-w-md border bg-background p-5 shadow-lg"
          >
            <h2 id="overview-delete-title" className="text-base font-semibold">删除作品</h2>
            <p id="overview-delete-description" className="mt-2 text-sm text-muted-foreground">
              确定删除「{detail.title}」及其全部内容吗？此操作无法撤销。
            </p>
            {remove.isError ? <p className="mt-3 text-sm text-destructive">{remove.error.message}</p> : null}
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" disabled={remove.isPending} onClick={() => setConfirmDelete(false)}>
                取消
              </Button>
              <Button
                variant="destructive"
                disabled={remove.isPending}
                onClick={() => remove.mutate()}
              >
                {remove.isPending ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Trash2 data-icon="inline-start" />}
                删除作品
              </Button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function statusLabel(status: CharacterDto["status"]) {
  if (status === "approved") return "已确认";
  if (status === "in_review") return "待审阅";
  return "草稿";
}

function CastRoster({
  characters,
  approvedCount,
  lockedCount,
  studioHref,
  loading,
  onRefresh,
}: {
  projectId: string;
  characters: CharacterDto[];
  approvedCount: number;
  lockedCount: number;
  studioHref: string;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold">全剧角色库</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            角色属于整部作品，各话共用同一批人。工作室「作品角色」编辑的就是这里；某一话只决定谁出场，不会单独另建一套角色库。
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            共 {characters.length} 人 · 已确认 {approvedCount} · 定妆锁定 {lockedCount}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onRefresh} disabled={loading}>
            刷新
          </Button>
          <ButtonLink href={studioHref} size="sm">
            <Users data-icon="inline-start" />
            在工作室编辑
          </ButtonLink>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">正在加载角色…</p>
      ) : characters.length === 0 ? (
        <div className="rounded-xl border px-6 py-12 text-center">
          <Users className="mx-auto size-8 text-muted-foreground" aria-hidden />
          <h3 className="mt-3 text-sm font-medium">还没有角色</h3>
          <p className="mt-1 text-sm text-muted-foreground">先进入工作室生成或手动建立角色，并建议锁定定妆后再出图。</p>
          <ButtonLink href={studioHref} className="mt-4">
            去建立角色
          </ButtonLink>
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {characters.map((character) => {
            const imageUrl = character.reference_asset_id
              ? `/api/v1/assets/${character.reference_asset_id}`
              : "";
            return (
              <li key={character.id} className="overflow-hidden rounded-xl border bg-card">
                <div className="relative aspect-[4/3] bg-muted">
                  {imageUrl ? (
                    <img src={imageUrl} alt="" className="absolute inset-0 size-full object-cover" />
                  ) : (
                    <div className="flex size-full items-center justify-center text-sm text-muted-foreground">
                      暂无定妆图
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-2 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate font-medium">{character.name}</h3>
                      <p className="truncate text-xs text-muted-foreground">
                        {character.profile.role || "未标注身份"}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <Badge variant={character.status === "approved" ? "secondary" : "outline"}>
                        {statusLabel(character.status)}
                      </Badge>
                      {character.reference_locked ? (
                        <Badge variant="outline">定妆锁定</Badge>
                      ) : null}
                    </div>
                  </div>
                  {character.profile.appearance ? (
                    <p className="line-clamp-2 text-xs text-muted-foreground">{character.profile.appearance}</p>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function ChapterList({
  projectId,
  projectTitle,
  episodes,
  onChanged,
}: {
  projectId: string;
  projectTitle: string;
  episodes: { id: string; title: string; synopsis: string; summary?: string; position: number }[];
  onChanged: () => void;
}) {
  const navigate = useNavigate();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const rowRefs = useRef<Record<string, HTMLLIElement | null>>({});
  const continueNext = useMutation({
    mutationFn: async (): Promise<
      | { kind: "stay"; episodeId: string; toast: string }
      | { kind: "studio"; episodeId: string; toast: string }
      | { kind: "created"; episodeId: string }
    > => {
      // First episode without summary is the continuity frontier (SERIAL-03 / F05).
      const frontierIdx = episodes.findIndex((episode) => !(episode.summary ?? "").trim());
      if (frontierIdx === 0) {
        const first = episodes[0]!;
        return {
          kind: "stay",
          episodeId: first.id,
          toast: `请先为「${first.title}」生成摘要，再续写下一话`,
        };
      }
      if (frontierIdx > 0) {
        const target = episodes[frontierIdx]!;
        return {
          kind: "studio",
          episodeId: target.id,
          toast: `已打开「${target.title}」；该话尚无摘要，可先出分镜或稍后补摘要`,
        };
      }
      const next = episodes.length + 1;
      const created = await createEpisode(projectId, {
        title: `第 ${next} 话`,
        synopsis: "待补充本话梗概",
        panel_count: 8,
      });
      return { kind: "created", episodeId: created.id };
    },
    onSuccess: (result) => {
      onChanged();
      if (result.kind === "stay") {
        toast.message(result.toast);
        rowRefs.current[result.episodeId]?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      if (result.kind === "studio") {
        toast.message(result.toast);
      } else {
        toast.success("已创建下一话");
      }
      navigate(`/projects/${projectId}/studio?episodeId=${result.episodeId}`);
    },
    onError: (error) => toast.error("续写失败", { description: error.message }),
  });

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          下一话生成分镜前须完成上一话摘要；跨话成册请用合集下载。
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={episodes.length === 0} onClick={() => setExportOpen(true)}>
            <Files data-icon="inline-start" />
            合集下载
          </Button>
          <Button size="sm" onClick={() => continueNext.mutate()} disabled={continueNext.isPending}>
            {continueNext.isPending ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Plus data-icon="inline-start" />}
            续写下一话
          </Button>
        </div>
      </div>
      {exportOpen ? (
        <AnthologyExportPanel
          projectId={projectId}
          projectTitle={projectTitle}
          episodes={episodes}
          onClose={() => setExportOpen(false)}
        />
      ) : null}
      <ul className="flex flex-col divide-y rounded-xl border">
        {episodes.map((episode, index) => (
          <li
            key={episode.id}
            ref={(node) => {
              rowRefs.current[episode.id] = node;
            }}
            className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center"
          >
            <div className="min-w-0 flex-1">
              <p className="text-xs tabular-nums text-muted-foreground">第 {index + 1} 话</p>
              <h3 className="font-medium">{episode.title}</h3>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{episode.synopsis}</p>
              {episode.summary ? (
                <p className="mt-2 text-xs text-muted-foreground">摘要：{episode.summary}</p>
              ) : (
                <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                  {index === 0
                    ? "尚未生成摘要（续写下一话前需要）"
                    : "规划/未开作 · 可进工作室开始本话"}
                </p>
              )}
            </div>
            <EpisodeRowActions
              projectId={projectId}
              episodeId={episode.id}
              hasSummary={Boolean(episode.summary)}
              busy={busyId === episode.id}
              onGenerateSummary={async () => {
                setBusyId(episode.id);
                try {
                  await generateEpisodeSummary(episode.id);
                  toast.success("摘要已生成");
                  onChanged();
                } catch (error) {
                  toast.error("生成摘要失败", { description: error instanceof Error ? error.message : undefined });
                } finally {
                  setBusyId(null);
                }
              }}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

function EpisodeRowActions({
  projectId,
  episodeId,
  hasSummary,
  busy,
  onGenerateSummary,
}: {
  projectId: string;
  episodeId: string;
  hasSummary: boolean;
  busy: boolean;
  onGenerateSummary: () => void | Promise<void>;
}) {
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreId = useId();
  const moreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!moreOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!moreRef.current?.contains(event.target as Node)) setMoreOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMoreOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [moreOpen]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="sm" onClick={() => navigate(`/projects/${projectId}/studio?episodeId=${episodeId}`)}>
        <PenLine data-icon="inline-start" />
        工作室
      </Button>
      <Button size="sm" variant="outline" disabled={busy} onClick={() => void onGenerateSummary()}>
        <ScrollText data-icon="inline-start" />
        {hasSummary ? "更新摘要" : "生成摘要"}
      </Button>
      <div className="relative" ref={moreRef}>
        <Button
          size="sm"
          variant="ghost"
          aria-haspopup="menu"
          aria-expanded={moreOpen}
          aria-controls={moreId}
          onClick={() => setMoreOpen((open) => !open)}
        >
          更多
          <ChevronDown className={cn("size-3.5", moreOpen && "rotate-180")} aria-hidden />
        </Button>
        {moreOpen ? (
          <div
            id={moreId}
            role="menu"
            aria-label="本话更多操作"
            className="absolute right-0 z-20 mt-1 w-44 rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
          >
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm hover:bg-accent"
              onClick={() => {
                setMoreOpen(false);
                navigate(`/projects/${projectId}/read/${episodeId}`);
              }}
            >
              <BookOpen className="size-4 text-muted-foreground" aria-hidden />
              阅读
            </button>
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm hover:bg-accent"
              onClick={() => {
                setMoreOpen(false);
                navigate(`/projects/${projectId}/layout/${episodeId}`);
              }}
            >
              <LayoutTemplate className="size-4 text-muted-foreground" aria-hidden />
              成稿排版
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function AnthologyExportPanel({
  projectId,
  projectTitle,
  episodes,
  onClose,
}: {
  projectId: string;
  projectTitle: string;
  episodes: { id: string; title: string; synopsis: string; summary?: string; position: number }[];
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set(episodes.map((item) => item.id)));
  const [format, setFormat] = useState<"png_zip" | "pdf">("png_zip");
  const [busy, setBusy] = useState(false);

  const toggle = (id: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const runExport = async () => {
    const episodeIds = episodes.filter((item) => selected.has(item.id)).map((item) => item.id);
    if (episodeIds.length === 0) {
      toast.error("请至少选择一话");
      return;
    }
    setBusy(true);
    try {
      const { data, error } = await api.POST("/projects/{project_id}/exports", {
        params: { path: { project_id: projectId } },
        body: { format, episode_ids: episodeIds, include_unapproved_panels: true },
      });
      if (error || !data) throw toApiError(error, "无法创建合集导出任务");
      const task = await waitForGenerationTask(appQueryClient, data.id);
      const result = task.result;
      if (!result || !("download_url" in result)) throw new Error("导出任务未返回下载地址");
      const response = await fetch(result.download_url, { credentials: "include" });
      if (!response.ok) throw new Error("下载文件失败");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      const disposition = response.headers.get("content-disposition") ?? "";
      const utf8Name = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1];
      const asciiName = /filename="([^"]+)"/i.exec(disposition)?.[1];
      const fromHeader = utf8Name ? decodeURIComponent(utf8Name) : asciiName;
      const base = (projectTitle || "anthology").replace(/[\\/:*?"<>|]+/g, "_").trim() || "anthology";
      const fallback = format === "pdf" ? `${base}-合集.pdf` : `${base}-合集.zip`;
      const preferred = fromHeader || fallback;
      anchor.download = preferred.match(/\.(zip|pdf)$/i) ? preferred : fallback;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success(format === "pdf" ? "合集 PDF 已导出" : "合集 ZIP 已导出");
      onClose();
    } catch (error) {
      toast.error("合集导出失败", { description: error instanceof Error ? error.message : undefined });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">合集下载</h2>
          <p className="mt-1 text-xs text-muted-foreground">勾选要收录的话，下载跨话分页 ZIP 或一本 PDF（制作预览，非成稿导出）。</p>
        </div>
        <Button size="sm" variant="ghost" onClick={onClose} disabled={busy}>
          取消
        </Button>
      </div>
      <ul className="mt-3 flex max-h-56 flex-col gap-1 overflow-y-auto">
        {episodes.map((episode, index) => (
          <li key={episode.id}>
            <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/60">
              <input
                type="checkbox"
                checked={selected.has(episode.id)}
                onChange={() => toggle(episode.id)}
                disabled={busy}
              />
              <span className="tabular-nums text-muted-foreground">#{index + 1}</span>
              <span className="truncate">{episode.title}</span>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="radio"
            name="anthology-format"
            checked={format === "png_zip"}
            onChange={() => setFormat("png_zip")}
            disabled={busy}
          />
          PNG ZIP
        </label>
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="radio"
            name="anthology-format"
            checked={format === "pdf"}
            onChange={() => setFormat("pdf")}
            disabled={busy}
          />
          PDF
        </label>
        <Button size="sm" className="ml-auto" disabled={busy || selected.size === 0} onClick={() => void runExport()}>
          {busy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Files data-icon="inline-start" />}
          {busy ? "导出中…" : "开始导出"}
        </Button>
      </div>
    </div>
  );
}

function BibleForm({
  projectId,
  worldSetting,
  styleRules,
  negativePrompt,
  styleSeed,
  onSaved,
}: {
  projectId: string;
  worldSetting: string;
  styleRules: string;
  negativePrompt: string;
  styleSeed: number | null;
  onSaved: () => void;
}) {
  const [world, setWorld] = useState(worldSetting);
  const [rules, setRules] = useState(styleRules);
  const [negative, setNegative] = useState(negativePrompt);
  const [seed, setSeed] = useState(styleSeed?.toString() ?? "");
  const [saving, setSaving] = useState(false);
  const parsedSeed = seed.trim() === "" ? null : Number(seed);
  const seedValid = parsedSeed === null || (Number.isInteger(parsedSeed) && parsedSeed >= 0);

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold">世界观</h2>
        <Textarea rows={6} value={world} onChange={(e) => setWorld(e.target.value)} />
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold">画风规则</h2>
        <p className="text-xs text-muted-foreground">自动附加到本作品每一次出图，让画风更统一。</p>
        <Textarea rows={3} value={rules} onChange={(e) => setRules(e.target.value)} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1.5 text-xs font-medium">
          作品负向提示词
          <Textarea rows={3} value={negative} onChange={(e) => setNegative(e.target.value)} />
        </label>
        <label className="grid gap-1.5 text-xs font-medium">
          Style seed（可选）
          <Input value={seed} onChange={(e) => setSeed(e.target.value)} inputMode="numeric" aria-invalid={!seedValid} />
        </label>
      </div>
      <Button
        disabled={saving || !seedValid}
        onClick={async () => {
          setSaving(true);
          try {
            await updateProjectBible(projectId, {
              world_setting: world,
              style_rules: rules,
              negative_prompt: negative,
              style_seed: parsedSeed,
            });
            toast.success("设定集已保存");
            onSaved();
          } catch (error) {
            toast.error("保存失败", { description: error instanceof Error ? error.message : undefined });
          } finally {
            setSaving(false);
          }
        }}
      >
        {saving ? <Loader2 className="animate-spin" data-icon="inline-start" /> : null}
        保存设定集
      </Button>
    </section>
  );
}

function ThreadList({
  projectId,
  threads,
  onChanged,
}: {
  projectId: string;
  threads: PlotThread[];
  onChanged: () => void;
}) {
  const [text, setText] = useState("");
  return (
    <section className="flex flex-col gap-4">
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!text.trim()) return;
          try {
            await createPlotThread(projectId, { text: text.trim(), resolved: false });
            setText("");
            onChanged();
            toast.success("伏笔已添加");
          } catch (error) {
            toast.error("添加失败", { description: error instanceof Error ? error.message : undefined });
          }
        }}
      >
        <Input value={text} onChange={(e) => setText(e.target.value)} placeholder="写下一条伏笔" className="flex-1" />
        <Button type="submit"><Plus data-icon="inline-start" />添加</Button>
      </form>
      <ul className="flex flex-col divide-y rounded-xl border">
        {threads.length === 0 ? <li className="p-4 text-sm text-muted-foreground">还没有伏笔</li> : null}
        {threads.map((thread) => (
          <li key={thread.id} className="flex items-start gap-3 p-4">
            <p className={cn("min-w-0 flex-1 text-sm", thread.resolved && "text-muted-foreground line-through")}>{thread.text}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={async () => {
                await updatePlotThread(thread.id, { resolved: !thread.resolved });
                onChanged();
              }}
            >
              {thread.resolved ? "标为未回收" : "标为已回收"}
            </Button>
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label="删除伏笔"
              onClick={async () => {
                await deletePlotThread(thread.id);
                onChanged();
              }}
            >
              <Trash2 />
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
