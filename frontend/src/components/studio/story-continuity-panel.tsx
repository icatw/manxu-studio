'use client'

import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { getProjectContinuity } from '@/services/serial-api'
import { useStudio } from './studio-provider'

/** Read-only planned outline + continuity inject preview (EP2-OUTLINE-01 / EP2-CONTINUITY-01). */
export function StoryContinuityPanel() {
  const { projectId, episodeNumber, project, dispatch } = useStudio()
  /** 0-based position of the current episode — matches generation inject scope. */
  const beforePosition = episodeNumber - 1
  const continuity = useQuery({
    queryKey: ['project-continuity', projectId, beforePosition],
    queryFn: () => getProjectContinuity(projectId, { beforePosition }),
  })

  const planned = (continuity.data?.planned_chapters ?? []).find(
    (chapter) => chapter.episode_number === episodeNumber,
  )
  const previous = continuity.data?.previous_summaries ?? []
  const threads = continuity.data?.open_threads ?? []
  const canApplyPlan =
    Boolean(planned) &&
    (project.story.synopsis.trim() !== (planned?.synopsis ?? '').trim() ||
      project.story.title.trim() !== (planned?.title ?? '').trim())

  if (episodeNumber < 2 && !previous.length && !threads.length && !planned) {
    return (
      <p className="text-xs text-muted-foreground">
        生成分镜不会改写本话梗概；梗概是输入，分镜是输出。
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-dashed bg-muted/30 p-4 text-sm">
      <div>
        <h2 className="text-xs font-medium text-muted-foreground">连载上下文</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          生成本话分镜时会注入下列前情与伏笔；生成不会改写上方本话梗概。
        </p>
      </div>

      {continuity.isPending ? (
        <p className="text-xs text-muted-foreground">加载规划与前情…</p>
      ) : continuity.isError ? (
        <p className="text-xs text-destructive">无法加载连载上下文</p>
      ) : (
        <>
          {planned ? (
            <section className="space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-xs font-medium">本话规划原文</h3>
                {canApplyPlan ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      dispatch({
                        type: 'updateStory',
                        patch: {
                          title: planned.title.slice(0, 40),
                          synopsis: planned.synopsis.slice(0, 2000),
                        },
                      })
                    }
                  >
                    填入本话梗概
                  </Button>
                ) : null}
              </div>
              <p className="text-xs font-medium text-foreground">{planned.title}</p>
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                {planned.synopsis || '（规划无梗概）'}
              </p>
            </section>
          ) : episodeNumber >= 2 ? (
            <p className="text-xs text-muted-foreground">
              设定中暂无第 {episodeNumber} 话规划大纲；请手写本话梗概，勿沿用第 1 话开场。
            </p>
          ) : null}

          <section className="space-y-1.5">
            <h3 className="text-xs font-medium">将注入的前情摘要</h3>
            {previous.length === 0 ? (
              <p className="text-xs text-muted-foreground">尚无更早话的摘要（第 1 话请先在总览生成摘要）。</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {previous.map((item) => (
                  <li key={item.episode_id} className="rounded-md bg-background/80 px-2.5 py-2">
                    <p className="text-[11px] text-muted-foreground">
                      第 {item.position + 1} 话 · {item.title}
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed">{item.summary}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-1.5">
            <h3 className="text-xs font-medium">未回收伏笔</h3>
            {threads.length === 0 ? (
              <p className="text-xs text-muted-foreground">当前无未回收伏笔。</p>
            ) : (
              <ul className="list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                {threads.map((thread) => (
                  <li key={thread.id}>{thread.text}</li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  )
}
