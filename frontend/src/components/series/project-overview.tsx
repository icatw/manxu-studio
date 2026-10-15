import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ArrowLeft, BookOpen, Loader2, PenLine, Plus, ScrollText, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { createEpisode, deleteProject, listEpisodes } from "@/services/workspace-api";
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

type Tab = "chapters" | "bible" | "threads";

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

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center gap-3 border-b px-5">
        <ButtonLink href="/projects" variant="ghost" size="sm">
          <ArrowLeft data-icon="inline-start" />
          作品库
        </ButtonLink>
        <span className="text-sm text-muted-foreground">/</span>
        <span className="truncate text-sm font-medium">{detail.title}</span>
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
            <dl className="flex gap-6 pt-1 text-sm">
              <div><dt className="text-xs text-muted-foreground">章节</dt><dd className="text-lg font-semibold tabular-nums">{episodes.data?.length ?? 0}</dd></div>
              <div><dt className="text-xs text-muted-foreground">未回收伏笔</dt><dd className="text-lg font-semibold tabular-nums">{openThreads}</dd></div>
            </dl>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 border-b">
          <div role="tablist" aria-label="作品内容" className="flex gap-1">
            {([
              { id: "chapters" as const, label: "章节" },
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
          <Button variant="ghost" size="sm" className="mb-1.5 text-muted-foreground hover:text-destructive" disabled={remove.isPending} onClick={() => remove.mutate()}>
            <Trash2 data-icon="inline-start" />
            删除作品
          </Button>
        </div>

        {tab === "chapters" ? (
          <ChapterList
            projectId={projectId}
            episodes={episodes.data ?? []}
            onChanged={() => {
              void queryClient.invalidateQueries({ queryKey: ["episodes", projectId] });
              void project.refetch();
            }}
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
    </div>
  );
}

function ChapterList({
  projectId,
  episodes,
  onChanged,
}: {
  projectId: string;
  episodes: { id: string; title: string; synopsis: string; summary?: string; position: number }[];
  onChanged: () => void;
}) {
  const navigate = useNavigate();
  const [busyId, setBusyId] = useState<string | null>(null);
  const continueNext = useMutation({
    mutationFn: async () => {
      const next = episodes.length + 1;
      return createEpisode(projectId, {
        title: `第 ${next} 话`,
        synopsis: "待补充本话梗概",
        panel_count: 4,
      });
    },
    onSuccess: (episode) => {
      onChanged();
      navigate(`/projects/${projectId}/studio?episodeId=${episode.id}`);
    },
    onError: (error) => toast.error("续写失败", { description: error.message }),
  });

  return (
    <section className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => continueNext.mutate()} disabled={continueNext.isPending}>
          {continueNext.isPending ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Plus data-icon="inline-start" />}
          续写下一话
        </Button>
      </div>
      <ul className="flex flex-col divide-y rounded-xl border">
        {episodes.map((episode, index) => (
          <li key={episode.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1">
              <p className="text-xs tabular-nums text-muted-foreground">第 {index + 1} 话</p>
              <h3 className="font-medium">{episode.title}</h3>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{episode.synopsis}</p>
              {episode.summary ? <p className="mt-2 text-xs text-muted-foreground">摘要：{episode.summary}</p> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={busyId === episode.id}
                onClick={async () => {
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
              >
                <ScrollText data-icon="inline-start" />
                生成摘要
              </Button>
              <Button size="sm" variant="outline" onClick={() => navigate(`/projects/${projectId}/read/${episode.id}`)}>
                <BookOpen data-icon="inline-start" />
                阅读
              </Button>
              <Button size="sm" onClick={() => navigate(`/projects/${projectId}/studio?episodeId=${episode.id}`)}>
                <PenLine data-icon="inline-start" />
                工作室
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </section>
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
