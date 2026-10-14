'use client'

import type { ReactElement, ReactNode } from 'react'
import { AlertCircle, CheckCircle2, CircleDashed, Loader2 } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { PANEL_STATUS_LABELS, type PanelStatus } from '@/types/storyboard'

const STATUS_STYLES: Record<PanelStatus, string> = {
  draft: 'bg-muted text-muted-foreground',
  generating: 'bg-primary/15 text-primary',
  completed: 'bg-success/15 text-success',
  failed: 'bg-destructive/15 text-destructive',
}

const STATUS_ICONS: Record<PanelStatus, typeof CircleDashed> = {
  draft: CircleDashed,
  generating: Loader2,
  completed: CheckCircle2,
  failed: AlertCircle,
}

export function StatusBadge({
  status,
  progress,
  className,
}: {
  status: PanelStatus
  progress?: number
  className?: string
}) {
  const Icon = STATUS_ICONS[status]
  return (
    <span
      className={cn(
        'inline-flex h-5 shrink-0 items-center gap-1 rounded-full px-2 text-[11px] font-medium',
        STATUS_STYLES[status],
        className,
      )}
    >
      <Icon className={cn('size-3', status === 'generating' && 'animate-spin')} aria-hidden />
      {PANEL_STATUS_LABELS[status]}
      {status === 'generating' && typeof progress === 'number' && (
        <span className="tabular-nums">{progress}%</span>
      )}
    </span>
  )
}

export function StatusDot({ status }: { status: PanelStatus }) {
  return (
    <span
      aria-label={PANEL_STATUS_LABELS[status]}
      className={cn(
        'inline-block size-1.5 shrink-0 rounded-full',
        status === 'draft' && 'bg-muted-foreground/60',
        status === 'generating' && 'animate-pulse bg-primary',
        status === 'completed' && 'bg-success',
        status === 'failed' && 'bg-destructive',
      )}
    />
  )
}

export function WithTooltip({
  label,
  children,
  side = 'bottom',
}: {
  label: ReactNode
  children: ReactElement
  side?: 'top' | 'bottom' | 'left' | 'right'
}) {
  return (
    <Tooltip>
      <TooltipTrigger render={children} />
      <TooltipContent side={side}>{label}</TooltipContent>
    </Tooltip>
  )
}

export function FieldLabel({ htmlFor, children, hint }: { htmlFor?: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">
        {children}
      </label>
      {hint && <span className="text-[11px] text-muted-foreground/70">{hint}</span>}
    </div>
  )
}
