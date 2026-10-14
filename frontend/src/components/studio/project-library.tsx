import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { ArrowUpRight, FolderPlus, Loader2, LogOut, Settings, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { createEpisode, createProject, deleteProject, listProjects } from "@/services/workspace-api";

export function ProjectLibrary() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const account = useQuery({ queryKey: ["current-account"], queryFn: async () => (await api.GET("/auth/me")).data ?? null, retry: false });
  const logout = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/auth/logout");
      if (error) throw new Error("退出登录失败，请稍后重试");
    },
    onSuccess: () => window.location.assign("/"),
    onError: (error) => toast.error("退出登录失败", { description: error.message }),
  });
  const create = useMutation({
    mutationFn: async () => {
      const project = await createProject({
        title: title.trim(), synopsis: synopsis.trim(), genre: "都市", art_style: "电影感",
        aspect_ratio: "portrait",
      });
      const episode = await createEpisode(project.id, { title: project.title, synopsis: project.synopsis, panel_count: 4 });
      return { project, episode };
    },
    onSuccess: async ({ project, episode }) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}?episodeId=${episode.id}`);
    },
    onError: (error) => toast.error("创建项目失败", { description: error.message }),
  });
  const remove = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
    onError: (error) => toast.error("删除项目失败", { description: error.message }),
  });

  const openProject = async (id: string) => {
    try {
      const { data, error } = await api.GET("/projects/{project_id}/episodes", { params: { path: { project_id: id } } });
      if (error) throw new Error("读取故事单元失败");
      const episode = data?.[0] ?? await createEpisode(id, { title: "第一话", synopsis: "", panel_count: 4 });
      navigate(`/projects/${id}?episodeId=${episode.id}`);
    } catch (error) {
      toast.error("无法打开项目", { description: error instanceof Error ? error.message : undefined });
    }
  };

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center border-b px-5">
        <a className="flex items-center gap-2 text-sm font-semibold" href="/">
          <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">漫</span>
          漫序 Studio
        </a>
        <span className="ml-4 border-l pl-4 text-sm text-muted-foreground">作品库</span>
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground" role="status">
          <span className="size-1.5 rounded-full bg-success" />API 驱动的预制作工作区
        </div>
        <Button variant="ghost" size="sm" className="ml-2" onClick={() => navigate("/settings")}>
          {account.data?.avatar_url ? <img src={account.data.avatar_url} alt="" className="size-5 rounded-full" /> : <Settings />}
          <span className="hidden sm:inline">设置</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
          disabled={logout.isPending}
          onClick={() => logout.mutate()}
        >
          <LogOut aria-hidden />
          <span className="hidden sm:inline">退出登录</span>
        </Button>
      </header>
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section>
          <div className="mb-5 flex items-end justify-between gap-4">
            <div><h1 className="text-xl font-semibold">项目</h1><p className="mt-1 text-sm text-muted-foreground">故事、资产与分镜集中在一个工作区。</p></div>
            <span className="text-xs tabular-nums text-muted-foreground">{projects.data?.length ?? 0} 个项目</span>
          </div>
          {projects.isPending ? <p className="py-12 text-center text-sm text-muted-foreground">正在加载项目…</p> : null}
          {projects.isError ? <div className="border-y py-8 text-sm"><p>无法读取项目：{projects.error.message}</p><Button className="mt-3" variant="outline" onClick={() => void projects.refetch()}>重试</Button></div> : null}
          {projects.isSuccess && projects.data.length === 0 ? <div className="border-y py-12 text-center text-sm text-muted-foreground">还没有项目，先创建一个故事。</div> : null}
          <div className="divide-y border-y">
            {projects.data?.map((project) => (
              <article key={project.id} className="flex min-w-0 items-center gap-4 py-4">
                <div className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-sm font-medium">{project.title.slice(0, 1) || "漫"}</div>
                <button className="min-w-0 flex-1 text-left" onClick={() => void openProject(project.id)}>
                  <span className="block truncate text-sm font-medium">{project.title}</span>
                  <span className="mt-1 block truncate text-xs text-muted-foreground">{project.synopsis || "尚未填写故事梗概"}</span>
                </button>
                <span className="hidden text-xs text-muted-foreground sm:block">{new Date(project.updated_at).toLocaleDateString("zh-CN")}</span>
                <Button variant="ghost" size="icon-sm" aria-label={`打开${project.title}`} title="打开项目" onClick={() => void openProject(project.id)}><ArrowUpRight /></Button>
                <Button variant="ghost" size="icon-sm" aria-label={`删除${project.title}`} title="删除项目" disabled={remove.isPending} onClick={() => { if (window.confirm(`删除「${project.title}」及其全部内容？`)) remove.mutate(project.id); }}><Trash2 /></Button>
              </article>
            ))}
          </div>
        </section>
        <aside className="h-fit border-t pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
          <h2 className="text-sm font-semibold">新建项目</h2>
          <form className="mt-4 flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
            <label className="flex flex-col gap-1.5 text-xs font-medium">项目名称<Input required maxLength={60} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：雾港来信" /></label>
            <label className="flex flex-col gap-1.5 text-xs font-medium">故事梗概<Textarea required maxLength={300} rows={4} value={synopsis} onChange={(event) => setSynopsis(event.target.value)} placeholder="描述主角、冲突与转折" /></label>
            <Button type="submit" disabled={!title.trim() || !synopsis.trim() || create.isPending}>
              {create.isPending ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <FolderPlus data-icon="inline-start" />}
              创建并进入工作区
            </Button>
          </form>
          <p className="mt-4 text-xs leading-relaxed text-muted-foreground">当前生成服务为演示实现，返回结构化草稿与样例图。</p>
        </aside>
      </div>
    </main>
  );
}
