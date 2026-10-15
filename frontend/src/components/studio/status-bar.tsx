'use client'

import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useStudio } from './studio-provider'

export function StatusBar() {
  const { project, generation, selectPanel, setStage, storyBusy } = useStudio()
  const counts = project.panels.reduce(
    (acc, p) => ({ ...acc, [p.status]: acc[p.status] + 1 }),
    { draft: 0, generating: 0, completed: 0, failed: 0 },
  )
  const failed = project.panels.filter((p) => p.status === 'failed')
  const generatingPanels = project.panels.filter((p) => p.status === 'generating')
  const avgProgress = generatingPanels.length
    ? Math.round(generatingPanels.reduce((s, p) => s + p.progress, 0) / generatingPanels.length)
    : 0

  return (
    <footer
      className="flex h-9 shrink-0 items-center gap-4 border-t bg-sidebar px-3 text-xs text-muted-foreground"
      aria-label="生成状态"
    >
      <div className="flex items-center gap-1.5" role="status" aria-live="polite">
        <span
          className={cn('size-1.5 rounded-full', counts.generating ? 'animate-pulse bg-primary' : 'bg-success')}
          aria-hidden
        />
        {storyBusy ? (
          <span>AI 正在生成角色、场景与分镜…</span>
        ) : counts.generating ? (
          <span>
            正在生成 {counts.generating} 格 · <span className="tabular-nums">{avgProgress}%</span>
          </span>
        ) : (
          <span>空闲</span>
        )}
      </div>

      <span className="tabular-nums">
        已完成 {counts.completed} · 草稿 {counts.draft}
        {counts.failed > 0 && <span className="text-destructive"> · 失败 {counts.failed}</span>}
      </span>

      {failed.length > 0 && (
        <Button
          variant="ghost"
          size="xs"
          className="text-destructive hover:text-destructive"
          onClick={() => {
            setStage('storyboard')
            failed.forEach((p, i) => {
              if (i === 0) selectPanel(p.id)
              void generation.generateOne(p.id)
            })
          }}
        >
          <RefreshCw data-icon="inline-start" />
          重试失败项
        </Button>
      )}

      <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-muted-foreground">图像模型：{generation.providerName}</span>
    </footer>
  )
}
