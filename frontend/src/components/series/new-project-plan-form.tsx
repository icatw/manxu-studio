import { useState, useTransition } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AUDIENCES, GENRES, VISUAL_STYLES } from "@/lib/catalogs";
import { createProjectFromPlan, planProject, type ProjectPlanDraft } from "@/services/serial-api";

const CHAPTER_COUNTS = [3, 6, 8, 10, 12];

export function NewProjectPlanForm() {
  const navigate = useNavigate();
  const [premise, setPremise] = useState("");
  const [genre, setGenre] = useState<string>(GENRES[0]);
  const [style, setStyle] = useState<string>(VISUAL_STYLES[0]);
  const [audience, setAudience] = useState<string>(AUDIENCES[1]);
  const [chapterCount, setChapterCount] = useState(6);
  const [planning, setPlanning] = useState(false);
  const [plan, setPlan] = useState<ProjectPlanDraft | null>(null);
  const [creating, startCreate] = useTransition();

  const handlePlan = async () => {
    if (!premise.trim()) {
      toast.error("请先写下作品创意");
      return;
    }
    setPlanning(true);
    try {
      const draft = await planProject({
        premise: premise.trim(),
        genre,
        art_style: style,
        audience,
        chapter_count: chapterCount,
        aspect_ratio: "portrait",
      });
      setPlan(draft);
    } catch (error) {
      toast.error("策划失败", { description: error instanceof Error ? error.message : undefined });
    } finally {
      setPlanning(false);
    }
  };

  const handleCreate = () => {
    if (!plan) return;
    startCreate(async () => {
      try {
        const result = await createProjectFromPlan(plan);
        navigate(`/projects/${result.project.id}`);
      } catch (error) {
        toast.error("创建失败", { description: error instanceof Error ? error.message : undefined });
      }
    });
  };

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center gap-3 border-b px-5">
        <ButtonLink href="/projects" variant="ghost" size="sm">
          <ArrowLeft data-icon="inline-start" />
          作品库
        </ButtonLink>
        <h1 className="text-sm font-semibold">AI 策划新作品</h1>
      </header>
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-5 py-8">
        {!plan ? (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor="premise">作品创意</Label>
              <Textarea
                id="premise"
                rows={5}
                value={premise}
                onChange={(event) => setPremise(event.target.value)}
                placeholder="一句话或一段梗概：主角、冲突与奇观"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-1.5 text-xs font-medium">
                题材
                <select className="h-9 rounded-md border bg-background px-2" value={genre} onChange={(e) => setGenre(e.target.value)}>
                  {GENRES.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="grid gap-1.5 text-xs font-medium">
                画风
                <select className="h-9 rounded-md border bg-background px-2" value={style} onChange={(e) => setStyle(e.target.value)}>
                  {VISUAL_STYLES.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="grid gap-1.5 text-xs font-medium">
                受众
                <select className="h-9 rounded-md border bg-background px-2" value={audience} onChange={(e) => setAudience(e.target.value)}>
                  {AUDIENCES.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="grid gap-1.5 text-xs font-medium">
                第一季话数
                <select className="h-9 rounded-md border bg-background px-2" value={chapterCount} onChange={(e) => setChapterCount(Number(e.target.value))}>
                  {CHAPTER_COUNTS.map((item) => <option key={item} value={item}>{item} 话</option>)}
                </select>
              </label>
            </div>
            <Button onClick={() => void handlePlan()} disabled={planning || !premise.trim()}>
              {planning ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
              {planning ? "策划中…" : "生成季策划"}
            </Button>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium text-primary">策划完成 · 请确认</p>
              <Input value={plan.title} onChange={(e) => setPlan({ ...plan, title: e.target.value })} className="text-2xl font-semibold" aria-label="作品名" />
              <p className="text-sm text-muted-foreground">{plan.genre} · {plan.art_style} · {plan.audience}</p>
            </div>
            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold">世界观</h2>
              <Textarea rows={5} value={plan.world_setting} onChange={(e) => setPlan({ ...plan, world_setting: e.target.value })} aria-label="世界观" />
            </section>
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold">主要角色（{plan.characters.length}）</h2>
              <ul className="grid gap-3 sm:grid-cols-2">
                {plan.characters.map((character, index) => (
                  <li key={`${character.name}-${index}`} className="rounded-lg border p-3">
                    <p className="text-sm font-medium">{character.name}</p>
                    <p className="text-xs text-muted-foreground">{character.role}</p>
                    <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">{character.appearance}</p>
                  </li>
                ))}
              </ul>
            </section>
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold">第一季大纲（{plan.chapters.length} 话）</h2>
              <ol className="flex flex-col divide-y rounded-lg border">
                {plan.chapters.map((chapter, index) => (
                  <li key={`${chapter.title}-${index}`} className="flex gap-3 p-3">
                    <span className="w-12 shrink-0 text-xs tabular-nums text-muted-foreground">第 {index + 1} 话</span>
                    <div>
                      <p className="text-sm font-medium">{chapter.title}</p>
                      <p className="text-sm text-muted-foreground">{chapter.synopsis}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
            {plan.threads.length > 0 ? (
              <section className="flex flex-col gap-2">
                <h2 className="text-sm font-semibold">伏笔</h2>
                <ul className="flex flex-col gap-1.5 text-sm text-muted-foreground">
                  {plan.threads.map((thread, index) => (
                    <li key={`${thread.text}-${index}`}>
                      {thread.text}
                      <span className="ml-2 text-xs tabular-nums">
                        第 {thread.planted_in ?? "?"} 话埋下 → 第 {thread.payoff_in ?? "?"} 话回收
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            <div className="flex gap-2 border-t pt-4">
              <Button variant="outline" onClick={() => setPlan(null)} disabled={creating}>重新策划</Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? <Loader2 className="animate-spin" data-icon="inline-start" /> : null}
                确认创建作品
              </Button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
