import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { FolderPlus, Loader2, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { AccountMenu } from "@/components/account-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonLink } from "@/components/ui/button-link";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createEpisode, createProject, deleteProject, listProjects } from "@/services/workspace-api";

export function ProjectLibrary() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const [projectToDelete, setProjectToDelete] = useState<{ id: string; title: string } | null>(null);
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const create = useMutation({
    mutationFn: async () => {
      const project = await createProject({
        title: title.trim(), synopsis: synopsis.trim(), genre: "都市", art_style: "电影感",
        aspect_ratio: "portrait",
      });
      const episode = await createEpisode(project.id, { title: project.title, synopsis: project.synopsis, panel_count: 8 });
      return { project, episode };
    },
    onSuccess: async ({ project }) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}`);
    },
    onError: (error) => toast.error("创建作品失败", { description: error.message }),
  });
  const remove = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      setProjectToDelete(null);
    },
    onError: (error) => toast.error("删除作品失败", { description: error.message }),
  });

  const openProject = (id: string) => {
    navigate(`/projects/${id}`);
  };

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center border-b px-5">
        <a className="flex items-center gap-2 text-sm font-semibold" href="/">
          <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">漫</span>
          漫序 Studio
        </a>
        <span className="ml-4 border-l pl-4 text-sm text-muted-foreground">作品库</span>
        <AccountMenu className="ml-auto" showLibraryLink={false} />
      </header>
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section>
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold">我的作品</h1>
              <p className="mt-1 text-sm text-muted-foreground">故事、角色与分镜，按作品集中管理。</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs tabular-nums text-muted-foreground">{projects.data?.length ?? 0} 部作品</span>
              <ButtonLink href="/projects/new" size="sm" variant="outline">
                <Sparkles data-icon="inline-start" />
                AI 策划
              </ButtonLink>
            </div>
          </div>
          {projects.isPending ? <p className="py-12 text-center text-sm text-muted-foreground">正在加载作品…</p> : null}
          {projects.isError ? <div className="border-y py-8 text-sm"><p>无法读取作品：{projects.error.message}</p><Button className="mt-3" variant="outline" onClick={() => void projects.refetch()}>重试</Button></div> : null}
          {projects.isSuccess && projects.data.length === 0 ? <div className="border-y py-12 text-center text-sm text-muted-foreground">还没有作品，先创建一个故事。</div> : null}
          <ul className="grid gap-4 sm:grid-cols-2">
            {projects.data?.map((project) => (
              <li key={project.id}>
                <article className="group flex h-full flex-col overflow-hidden rounded-xl border bg-card transition-shadow hover:shadow-md">
                  <button
                    type="button"
                    className="relative aspect-[16/10] w-full bg-muted text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                    onClick={() => openProject(project.id)}
                    aria-label={`打开「${project.title}」`}
                  >
                    {project.cover_image_url ? (
                      <img src={project.cover_image_url} alt="" className="absolute inset-0 size-full object-cover transition-transform duration-300 group-hover:scale-[1.02]" />
                    ) : (
                      <div className="absolute inset-0 grid place-items-center text-3xl font-bold text-muted-foreground/40">
                        {project.title.slice(0, 2) || "漫"}
                      </div>
                    )}
                  </button>
                  <div className="flex flex-1 flex-col gap-2 p-4">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{project.genre}</Badge>
                      <span className="truncate text-xs text-muted-foreground">{project.art_style}</span>
                    </div>
                    <button type="button" className="text-left outline-none focus-visible:underline" onClick={() => openProject(project.id)}>
                      <h2 className="font-semibold">{project.title}</h2>
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{project.synopsis || "尚未填写故事梗概"}</p>
                    </button>
                    <div className="mt-auto flex items-center justify-between pt-2">
                      <span className="text-xs text-muted-foreground">{new Date(project.updated_at).toLocaleDateString("zh-CN")} 更新</span>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`删除${project.title}`}
                        title="删除作品"
                        disabled={remove.isPending}
                        onClick={() => setProjectToDelete({ id: project.id, title: project.title })}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </section>
        <aside className="h-fit border-t pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
          <h2 className="text-sm font-semibold">新建作品</h2>
          <form className="mt-4 flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
            <label className="flex flex-col gap-1.5 text-xs font-medium">作品名称<Input required maxLength={60} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：雾港来信" /></label>
            <label className="flex flex-col gap-1.5 text-xs font-medium">故事梗概<Textarea required maxLength={300} rows={4} value={synopsis} onChange={(event) => setSynopsis(event.target.value)} placeholder="描述主角、冲突与转折" /></label>
            <Button type="submit" disabled={!title.trim() || !synopsis.trim() || create.isPending}>
              {create.isPending ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <FolderPlus data-icon="inline-start" />}
              创建并打开总览
            </Button>
          </form>
          <p className="mt-4 text-xs leading-relaxed text-muted-foreground">出图模型可在设置中配置。</p>
        </aside>
      </div>
      {projectToDelete ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-project-title"
            aria-describedby="delete-project-description"
            className="w-full max-w-md border bg-background p-5 shadow-lg"
          >
            <h2 id="delete-project-title" className="text-base font-semibold">删除作品</h2>
            <p id="delete-project-description" className="mt-2 text-sm text-muted-foreground">
              确定删除「{projectToDelete.title}」及其全部内容吗？此操作无法撤销。
            </p>
            {remove.isError ? <p className="mt-3 text-sm text-destructive">{remove.error.message}</p> : null}
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" disabled={remove.isPending} onClick={() => setProjectToDelete(null)}>取消</Button>
              <Button
                variant="destructive"
                disabled={remove.isPending}
                onClick={() => remove.mutate(projectToDelete.id)}
              >
                {remove.isPending ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Trash2 data-icon="inline-start" />}
                删除作品
              </Button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
