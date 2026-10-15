'use client'

import Image from '@/components/ui/image'
import { AlertTriangle, ChevronLeft, ChevronRight, ImageOff, RefreshCw, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ASSET_SOURCE_SHORT } from '@/lib/asset-labels'
import { cn } from '@/lib/utils'
import { SHOT_TYPE_LABELS, type StoryboardPanel as Panel } from '@/types/storyboard'
import { StatusBadge, WithTooltip } from './shared'

interface Props {
  panel: Panel
  index: number
  total: number
  selected: boolean
  onSelect: () => void
  onMove: (direction: -1 | 1) => void
  onGenerate: () => void
  onCancel: () => void
}

const ASPECT_CLASS: Record<Panel['aspectRatio'], string> = {
  '16:9': 'aspect-video',
  '4:3': 'aspect-[4/3]',
  '1:1': 'aspect-square',
  '3:4': 'aspect-[3/4]',
}

export function StoryboardPanelCard({ panel, index, total, selected, onSelect, onMove, onGenerate, onCancel }: Props) {
  const generating = panel.status === 'generating'
  const bubbleRight = index % 2 === 1

  return (
    <article
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-lg bg-card ring-1 transition-shadow',
        selected ? 'ring-2 ring-primary shadow-[0_0_0_4px] shadow-primary/15' : 'ring-border hover:ring-foreground/20',
      )}
      aria-label={`第 ${panel.panelNumber} 格`}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        aria-label={`选择第 ${panel.panelNumber} 格进行编辑`}
        className="absolute inset-0 z-0 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />

      <div className={cn('pointer-events-none relative w-full overflow-hidden bg-muted', ASPECT_CLASS[panel.aspectRatio])}>
        {panel.imageUrl ? (
          <Image
            src={panel.imageUrl}
            alt={`第 ${panel.panelNumber} 格：${panel.scene}`}
            fill
            sizes="(min-width: 1280px) 480px, 50vw"
            className={cn('object-cover transition-opacity', generating && 'opacity-40')}
            priority={index < 2}
          />
        ) : (
          !generating &&
          panel.status !== 'failed' && (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <ImageOff className="size-6" aria-hidden />
              <span className="text-xs">尚未生成画面</span>
            </div>
          )
        )}

        {generating && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background/50 backdrop-blur-[2px]">
            <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-primary/10 via-transparent to-primary/5" />
            <span className="relative text-2xl font-semibold tabular-nums">{panel.progress}%</span>
            <div className="relative h-1 w-1/2 overflow-hidden rounded-full bg-foreground/10">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-150"
                style={{ width: `${panel.progress}%` }}
              />
            </div>
            <span className="relative text-xs text-muted-foreground">正在生成画面…</span>
          </div>
        )}

        {panel.status === 'failed' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-destructive/10 p-4 text-center">
            <AlertTriangle className="size-6 text-destructive" aria-hidden />
            <span className="text-xs font-medium text-destructive">生成失败</span>
            <span className="line-clamp-2 text-[11px] text-muted-foreground">{panel.errorMessage}</span>
          </div>
        )}

        {panel.dialogue.trim() && !generating && (
          <div
            className={cn(
              'absolute top-[5%] max-w-[62%] rounded-[1.25rem] border-2 border-neutral-900 bg-white px-3 py-1.5 text-center text-[13px] leading-snug font-bold text-neutral-900 shadow-md',
              bubbleRight ? 'right-[4%]' : 'left-[4%]',
            )}
          >
            <span className="line-clamp-3">{panel.dialogue}</span>
            <span
              aria-hidden
              className={cn(
                'absolute -bottom-[9px] size-4 rotate-45 border-r-2 border-b-2 border-neutral-900 bg-white',
                bubbleRight ? 'right-[28%]' : 'left-[28%]',
              )}
            />
          </div>
        )}

        <span className="absolute bottom-0 left-0 bg-neutral-950 px-2 py-0.5 text-xs font-bold text-white tabular-nums">
          {panel.panelNumber}
        </span>
        {panel.imageSource && panel.imageUrl && (
          <span className="absolute right-2 bottom-2 rounded bg-neutral-950/70 px-1.5 py-0.5 text-[10px] text-neutral-200 backdrop-blur">
            {ASSET_SOURCE_SHORT[panel.imageSource]}
          </span>
        )}
      </div>

      <div className="pointer-events-none flex items-start gap-2 p-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold">第 {panel.panelNumber} 格</span>
            <span className="rounded bg-muted px-1.5 py-px text-[11px] text-muted-foreground">
              {SHOT_TYPE_LABELS[panel.shotType]}
            </span>
            <span className="text-[11px] text-muted-foreground">{panel.aspectRatio}</span>
          </div>
          <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{panel.scene}</p>
        </div>
        <StatusBadge status={panel.status} progress={panel.progress} />
      </div>

      <div className="absolute top-2 left-1/2 z-10 flex -translate-x-1/2 items-center gap-0.5 rounded-md bg-popover/95 p-0.5 opacity-0 shadow-lg ring-1 ring-border backdrop-blur transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
        <WithTooltip label="向前移动">
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => onMove(-1)}
            disabled={index === 0}
            aria-label={`将第 ${panel.panelNumber} 格向前移动`}
          >
            <ChevronLeft />
          </Button>
        </WithTooltip>
        {generating ? (
          <WithTooltip label="停止跟踪">
            <Button variant="ghost" size="icon-xs" onClick={onCancel} aria-label={`停止跟踪第 ${panel.panelNumber} 格生成`}>
              <Square />
            </Button>
          </WithTooltip>
        ) : (
          <WithTooltip label={panel.imageUrl ? '重新生成画面' : '生成画面'}>
            <Button variant="ghost" size="icon-xs" onClick={onGenerate} aria-label={`生成第 ${panel.panelNumber} 格画面`}>
              <RefreshCw />
            </Button>
          </WithTooltip>
        )}
        <WithTooltip label="向后移动">
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => onMove(1)}
            disabled={index === total - 1}
            aria-label={`将第 ${panel.panelNumber} 格向后移动`}
          >
            <ChevronRight />
          </Button>
        </WithTooltip>
      </div>
    </article>
  )
}
