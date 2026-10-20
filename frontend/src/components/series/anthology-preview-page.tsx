import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { ArrowLeft, LayoutTemplate, Loader2 } from "lucide-react";
import { LetteringOverlay } from "@/components/series/lettering-overlay";
import { ButtonLink } from "@/components/ui/button-link";
import {
  getProjectAnthologyPreview,
  type AnthologyPreviewChapter,
} from "@/services/layout-api";

export function AnthologyPreviewPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const episodeIds = useMemo(
    () =>
      searchParams
        .get("episodes")
        ?.split(",")
        .map((item) => item.trim())
        .filter(Boolean) ?? [],
    [searchParams],
  );

  const preview = useQuery({
    queryKey: ["anthology-preview", projectId, episodeIds],
    queryFn: () => getProjectAnthologyPreview(projectId, episodeIds),
    enabled: Boolean(projectId) && episodeIds.length > 0,
  });

  if (episodeIds.length === 0) {
    return (
      <main className="grid min-h-dvh place-items-center bg-neutral-950 p-6 text-center text-neutral-100">
        <div>
          <h1 className="text-base font-semibold">未选择话次</h1>
          <p className="mt-2 text-sm text-neutral-400">请从作品总览勾选要连读的话。</p>
          <ButtonLink href={`/projects/${projectId}`} className="mt-4">
            返回作品
          </ButtonLink>
        </div>
      </main>
    );
  }

  if (preview.isPending) {
    return (
      <main className="grid min-h-dvh place-items-center bg-neutral-950 text-sm text-neutral-400">
        <span className="inline-flex items-center gap-2">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          正在加载合集预览…
        </span>
      </main>
    );
  }

  if (preview.isError || !preview.data) {
    return (
      <main className="grid min-h-dvh place-items-center bg-neutral-950 p-6 text-center text-neutral-100">
        <div>
          <h1 className="text-base font-semibold">无法打开合集预览</h1>
          <p className="mt-2 text-sm text-neutral-400">
            {preview.error instanceof Error ? preview.error.message : "请稍后重试"}
          </p>
          <ButtonLink href={`/projects/${projectId}`} className="mt-4">
            返回作品
          </ButtonLink>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-dvh bg-neutral-950 text-neutral-100">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-neutral-950/90 backdrop-blur">
        <div className="mx-auto flex h-12 max-w-xl items-center gap-3 px-4">
          <button
            type="button"
            className="flex min-w-0 items-center gap-1 text-sm text-neutral-400 hover:text-neutral-100"
            onClick={() => navigate(`/projects/${projectId}`)}
          >
            <ArrowLeft className="size-4 shrink-0" aria-hidden />
            <span className="truncate">返回作品</span>
          </button>
          <span className="ml-auto shrink-0 text-sm font-medium">合集预览</span>
        </div>
      </header>
      <main className="mx-auto flex max-w-xl flex-col pb-16">
        <p className="px-4 py-4 text-center text-xs text-neutral-500">
          成稿条连读 · 含字效叠层 · 非分镜阅读 · 非导出文件
        </p>
        {preview.data.chapters.map((chapter, index) => (
          <ChapterStrip
            key={chapter.episode_id}
            projectId={projectId}
            chapter={chapter}
            ordinal={index + 1}
          />
        ))}
      </main>
    </div>
  );
}

function ChapterStrip({
  projectId,
  chapter,
  ordinal,
}: {
  projectId: string;
  chapter: AnthologyPreviewChapter;
  ordinal: number;
}) {
  return (
    <section className="border-t border-white/10">
      <div className="sticky top-12 z-10 flex items-center justify-between gap-3 border-b border-white/5 bg-neutral-950/95 px-4 py-3 backdrop-blur">
        <div className="min-w-0">
          <p className="text-[11px] tabular-nums text-neutral-500">第 {ordinal} 话</p>
          <h2 className="truncate text-sm font-semibold">{chapter.title}</h2>
        </div>
        {!chapter.ready ? (
          <ButtonLink
            href={`/projects/${projectId}/layout/${chapter.episode_id}`}
            size="sm"
            variant="secondary"
          >
            <LayoutTemplate data-icon="inline-start" />
            去成稿排版
          </ButtonLink>
        ) : null}
      </div>
      {!chapter.ready || !chapter.preview ? (
        <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
          <p className="text-sm font-medium text-neutral-200">未排版</p>
          <p className="text-xs text-neutral-500">
            {chapter.skip_reason === "empty_slots"
              ? "本话布局尚无槽位，无法预览成稿条。"
              : "本话尚未建立竖条布局。其余话仍可继续下滚阅读。"}
          </p>
          <ButtonLink
            href={`/projects/${projectId}/layout/${chapter.episode_id}`}
            size="sm"
            variant="outline"
            className="mt-2 border-white/20 bg-transparent text-neutral-100"
          >
            去成稿排版
          </ButtonLink>
        </div>
      ) : (
        <ol className="flex flex-col">
          {chapter.preview.items.map((item, index) => (
            <li
              key={item.slot_id}
              className="relative flex flex-col overflow-hidden"
              style={{ marginBottom: item.gap_after_px }}
            >
              {item.image_url ? (
                <img
                  src={item.image_url}
                  alt={`第 ${ordinal} 话 · 第 ${index + 1} 格`}
                  className="w-full bg-neutral-900 object-cover"
                  style={{ height: item.height_px }}
                />
              ) : (
                <div
                  className="flex w-full items-center justify-center bg-neutral-900 px-4 text-center text-sm text-neutral-500"
                  style={{ height: item.height_px }}
                >
                  画面未就绪
                </div>
              )}
              <LetteringOverlay items={item.lettering ?? []} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
