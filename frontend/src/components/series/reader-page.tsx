import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { ChevronLeft, ChevronRight, LayoutTemplate, List, PenLine } from "lucide-react";
import { ButtonLink } from "@/components/ui/button-link";
import { getEpisodeReader } from "@/services/serial-api";

export function ReaderPage() {
  const { projectId = "", episodeId = "" } = useParams();
  const navigate = useNavigate();
  const reader = useQuery({
    queryKey: ["reader", episodeId],
    queryFn: () => getEpisodeReader(episodeId),
    enabled: Boolean(episodeId),
  });

  if (reader.isPending) {
    return <main className="grid min-h-dvh place-items-center bg-neutral-950 text-sm text-neutral-400">正在打开阅读页…</main>;
  }
  if (reader.isError || !reader.data) {
    return (
      <main className="grid min-h-dvh place-items-center bg-neutral-950 p-6 text-center text-neutral-100">
        <div>
          <h1 className="text-base font-semibold">无法打开阅读页</h1>
          <ButtonLink href={`/projects/${projectId}`} className="mt-4">返回作品</ButtonLink>
        </div>
      </main>
    );
  }

  const { episode, panels, previous_episode_id, next_episode_id } = reader.data;

  return (
    <div className="min-h-dvh bg-neutral-950 text-neutral-100">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-neutral-950/90 backdrop-blur">
        <div className="mx-auto flex h-12 max-w-2xl items-center gap-3 px-4">
          <button
            type="button"
            className="flex min-w-0 items-center gap-1 text-sm text-neutral-400 hover:text-neutral-100"
            onClick={() => navigate(`/projects/${projectId}`)}
          >
            <ChevronLeft className="size-4 shrink-0" aria-hidden />
            <span className="truncate">返回作品</span>
          </button>
          <span className="ml-auto shrink-0 text-sm font-medium tabular-nums">{episode.title}</span>
        </div>
      </header>
      <main className="mx-auto flex max-w-2xl flex-col">
        <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
          <h1 className="text-2xl font-semibold text-balance">{episode.title}</h1>
          <p className="text-xs text-neutral-500">分镜阅读（制作态）· 成稿布局与导出请用「成稿排版」</p>
        </div>
        <ol className="flex flex-col gap-1">
          {panels.map((panel, index) => (
            <li key={panel.id} className="flex flex-col">
              {panel.image_url ? (
                <div className="relative aspect-[4/3] w-full bg-neutral-900">
                  <img src={panel.image_url} alt={panel.action || `第 ${index + 1} 格`} className="absolute inset-0 size-full object-cover" />
                </div>
              ) : (
                <div className="flex aspect-[4/3] w-full items-center justify-center bg-neutral-900 px-8 text-center text-sm text-neutral-500">
                  {panel.action || "画面尚未生成"}
                </div>
              )}
              {panel.dialogue ? (
                <p className="relative mx-4 -mt-6 mb-4 self-start rounded-2xl rounded-tl-sm bg-white px-4 py-2.5 text-sm leading-relaxed text-neutral-900 shadow-lg">
                  {panel.dialogue}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
        <nav aria-label="话次导航" className="flex flex-col items-center gap-6 px-6 py-16">
          <p className="text-sm text-neutral-400">— {episode.title} 完 —</p>
          <div className="flex w-full items-center justify-between gap-3">
            {previous_episode_id ? (
              <ButtonLink href={`/projects/${projectId}/read/${previous_episode_id}`} variant="secondary" size="sm">
                <ChevronLeft data-icon="inline-start" />
                上一话
              </ButtonLink>
            ) : <span />}
            <div className="flex items-center gap-2">
              <ButtonLink href={`/projects/${projectId}`} variant="ghost" size="sm" className="text-neutral-300 hover:bg-white/10 hover:text-white">
                <List data-icon="inline-start" />
                目录
              </ButtonLink>
              <ButtonLink
                href={`/projects/${projectId}/layout/${episode.id}`}
                variant="ghost"
                size="sm"
                className="text-neutral-300 hover:bg-white/10 hover:text-white"
              >
                <LayoutTemplate data-icon="inline-start" />
                成稿排版
              </ButtonLink>
              <ButtonLink href={`/projects/${projectId}/studio?episodeId=${episode.id}`} variant="ghost" size="sm" className="text-neutral-300 hover:bg-white/10 hover:text-white">
                <PenLine data-icon="inline-start" />
                编辑
              </ButtonLink>
            </div>
            {next_episode_id ? (
              <ButtonLink href={`/projects/${projectId}/read/${next_episode_id}`} variant="secondary" size="sm">
                下一话
                <ChevronRight data-icon="inline-end" />
              </ButtonLink>
            ) : <span />}
          </div>
        </nav>
      </main>
    </div>
  );
}
