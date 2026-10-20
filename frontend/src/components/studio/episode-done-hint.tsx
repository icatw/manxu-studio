'use client'

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { LayoutTemplate, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useStudio } from './studio-provider'

function storageKey(episodeId: string) {
  return `manxu:episode-done-hint:${episodeId}`
}

/** Non-blocking “本话画面就绪” nudge toward manuscript layout (0044 P1). */
export function EpisodeDoneHint() {
  const { project, episodeId, projectId, stage } = useStudio()
  const navigate = useNavigate()
  const imagedCount = project.panels.filter((panel) => Boolean(panel.imageUrl)).length
  const [dismissed, setDismissed] = useState(true)

  useEffect(() => {
    if (!episodeId) {
      setDismissed(true)
      return
    }
    try {
      setDismissed(sessionStorage.getItem(storageKey(episodeId)) === '1')
    } catch {
      setDismissed(false)
    }
  }, [episodeId])

  const visible =
    Boolean(episodeId) &&
    stage === 'storyboard' &&
    imagedCount >= 1 &&
    !dismissed

  if (!visible) return null

  const dismiss = () => {
    setDismissed(true)
    if (!episodeId) return
    try {
      sessionStorage.setItem(storageKey(episodeId), '1')
    } catch {
      /* ignore quota / private mode */
    }
  }

  return (
    <div
      role="status"
      className="flex shrink-0 flex-wrap items-center gap-2 border-b bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
    >
      <p className="min-w-0 flex-1 text-pretty">
        本话已有画面 → 可去<strong className="font-medium text-foreground">成稿排版</strong>
        ；带走文件用成稿页的<strong className="font-medium text-foreground">导出成稿</strong>
        （勿与顶栏「制作导出」混淆）。
      </p>
      <div className="flex shrink-0 items-center gap-1.5">
        <Button
          size="xs"
          variant="secondary"
          onClick={() => {
            dismiss()
            navigate(`/projects/${projectId}/layout/${episodeId}`)
          }}
        >
          <LayoutTemplate data-icon="inline-start" />
          成稿排版
        </Button>
        <Button size="xs" variant="ghost" onClick={dismiss}>
          知道了
        </Button>
        <Button size="icon-xs" variant="ghost" aria-label="关闭提示" onClick={dismiss}>
          <X />
        </Button>
      </div>
    </div>
  )
}
