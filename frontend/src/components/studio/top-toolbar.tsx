'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import {
  ArrowLeft,
  Check,
  ChevronDown,
  CloudOff,
  Download,
  Eye,
  FileJson,
  Files,
  LayoutTemplate,
  Loader2,
  Redo2,
  Sparkles,
  Undo2,
} from 'lucide-react'
import { toast } from 'sonner'
import { AccountMenu } from '@/components/account-menu'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api/client'
import { waitForGenerationTask } from '@/lib/generation-task'
import { queryClient } from '@/lib/query-client'
import { cn } from '@/lib/utils'
import { useStudio } from './studio-provider'
import { WithTooltip } from './shared'
import { RegenerateConfirmDialog } from './regenerate-confirm-dialog'

type ExportFormat = 'png' | 'png_zip' | 'production_json'

function formatTime(date: Date) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function SaveIndicator() {
  const { saveState, lastSavedAt } = useStudio()
  if (saveState === 'saving')
    return (
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        保存中…
      </span>
    )
  if (saveState === 'error')
    return (
      <span className="flex items-center gap-1.5 text-xs text-destructive">
        <CloudOff className="size-3" aria-hidden />
        保存失败
      </span>
    )
  if (saveState === 'saved' && lastSavedAt)
    return (
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Check className="size-3 text-success" aria-hidden />
        已保存 · {formatTime(lastSavedAt)}
      </span>
    )
  return null
}

export function TopToolbar() {
  const { project, dispatch, canUndo, canRedo, undo, redo, setPreviewOpen, storyBusy, generateFromStory, episodeId, projectId } = useStudio()
  const navigate = useNavigate()
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const exportMenuId = useId()
  const exportWrapRef = useRef<HTMLDivElement>(null)

  const hasPanels = project.panels.length > 0
  const hasWork = project.panels.some((p) => p.imageUrl || p.dialogue)
  const exporting = exportingFormat !== null

  useEffect(() => {
    if (!exportOpen) return
    const onPointerDown = (event: MouseEvent) => {
      if (!exportWrapRef.current?.contains(event.target as Node)) setExportOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setExportOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [exportOpen])

  const handleExport = async (format: ExportFormat) => {
    if (!hasPanels) {
      toast.error('没有可导出的分镜')
      return
    }
    setExportingFormat(format)
    try {
      const { data, error } = await api.POST('/episodes/{episode_id}/exports', {
        params: { path: { episode_id: episodeId } },
        body: { format, include_unapproved_panels: true },
      })
      if (error || !data) throw new Error('无法创建导出任务')
      const task = await waitForGenerationTask(queryClient, data.id)
      const result = task.result
      if (!result || !('download_url' in result)) throw new Error('导出任务未返回下载地址')
      const response = await fetch(result.download_url, { credentials: 'include' })
      if (!response.ok) throw new Error('下载文件失败')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      const disposition = response.headers.get('content-disposition') ?? ''
      const utf8Name = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1]
      const asciiName = /filename="([^"]+)"/i.exec(disposition)?.[1]
      const fromHeader = utf8Name ? decodeURIComponent(utf8Name) : asciiName
      const fallbackBase = (project.story.title || 'storyboard').replace(/[\\/:*?"<>|]+/g, '_').trim() || 'storyboard'
      const fallback =
        format === 'png' ? `${fallbackBase}.png` : format === 'png_zip' ? `${fallbackBase}.zip` : `${fallbackBase}-production.json`
      const preferred = fromHeader || fallback
      anchor.download = preferred.match(/\.(png|zip|json)$/i) ? preferred : fallback
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
      toast.success(
        format === 'png' ? '长图 PNG 已导出' : format === 'png_zip' ? '分页 ZIP 已导出' : '制作资料已导出',
      )
    } catch (error) {
      toast.error('导出失败', { description: error instanceof Error ? error.message : undefined })
    } finally {
      setExportingFormat(null)
    }
  }

  const handleGenerate = () => {
    if (hasWork) setConfirmOpen(true)
    else void generateFromStory({ regenerateCharacters: false })
  }

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b bg-sidebar px-3">
      <div className="flex items-center gap-2 pr-1">
        <Button variant="ghost" size="icon-sm" aria-label="返回作品总览" title="返回作品总览" onClick={() => navigate(`/projects/${projectId}`)}>
          <ArrowLeft />
        </Button>
        <div
          aria-hidden
          className="flex size-7 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground"
        >
          漫
        </div>
        <span className="hidden text-sm font-semibold tracking-tight md:inline">漫序 Studio</span>
      </div>
      <div className="h-5 w-px bg-border" aria-hidden />

      <div className="flex min-w-0 flex-1 items-center gap-3">
        <>
            <label htmlFor="project-title" className="sr-only">
              作品标题
            </label>
            <input
              id="project-title"
              value={project.title}
              onChange={(e) => dispatch({ type: 'setTitle', title: e.target.value })}
              placeholder="未命名作品"
              maxLength={60}
              className="h-8 w-full min-w-0 max-w-72 truncate rounded-md border border-transparent bg-transparent px-2 text-sm font-medium outline-none transition-colors hover:border-input focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
            />
        </>
        <div className="hidden lg:block">
          <SaveIndicator />
        </div>
      </div>

      <div className="flex items-center gap-1">
        <WithTooltip label="撤销编辑 (⌘Z)">
          <Button
            className="hidden md:inline-flex"
            variant="ghost"
            size="icon-sm"
            onClick={undo}
            disabled={!canUndo}
            aria-label="撤销编辑"
            title="撤销编辑 (⌘Z)"
          >
            <Undo2 />
          </Button>
        </WithTooltip>
        <WithTooltip label="重做编辑 (⇧⌘Z)">
          <Button
            className="hidden md:inline-flex"
            variant="ghost"
            size="icon-sm"
            onClick={redo}
            disabled={!canRedo}
            aria-label="重做编辑"
            title="重做编辑 (⇧⌘Z)"
          >
            <Redo2 />
          </Button>
        </WithTooltip>
        <div className="mx-1 hidden h-5 w-px bg-border md:block" aria-hidden />
        <Button
          variant="ghost"
          size="icon-sm"
          className="md:w-auto md:px-2.5"
          aria-label="制作预览"
          title="按分镜序预览本话（制作态，非成稿布局）"
          onClick={() => setPreviewOpen(true)}
          disabled={!hasPanels}
        >
          <Eye data-icon="inline-start" />
          <span className="hidden md:inline">制作预览</span>
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          className="md:w-auto md:px-2.5"
          aria-label="成稿排版"
          title="成稿排版"
          disabled={!hasPanels || !episodeId}
          onClick={() => navigate(`/projects/${projectId}/layout/${episodeId}`)}
        >
          <LayoutTemplate data-icon="inline-start" />
          <span className="hidden md:inline">成稿排版</span>
        </Button>
        <div className="relative" ref={exportWrapRef}>
          <Button
            variant="outline"
            size="icon-sm"
            className="md:w-auto md:px-2.5"
            aria-label="制作导出"
            aria-haspopup="menu"
            aria-expanded={exportOpen}
            aria-controls={exportMenuId}
            title="制作导出（长图 / 分页 ZIP / 制作资料）· 非成稿导出"
            disabled={!hasPanels || exporting}
            onClick={() => setExportOpen((open) => !open)}
          >
            {exporting ? (
              <Loader2 className="animate-spin" data-icon="inline-start" />
            ) : (
              <Download data-icon="inline-start" />
            )}
            <span className="hidden md:inline">制作导出</span>
            <ChevronDown className={cn('hidden size-3.5 md:inline', exportOpen && 'rotate-180')} aria-hidden />
          </Button>
          {exportOpen ? (
            <div
              id={exportMenuId}
              role="menu"
              aria-label="制作导出格式"
              className="absolute right-0 z-40 mt-1 w-56 rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
            >
              <p className="px-2 py-1.5 text-[11px] text-muted-foreground">制作预览导出 · 非成稿导出</p>
              {(
                [
                  {
                    format: 'png' as const,
                    label: '长图 PNG',
                    description: '本话竖向一条长图',
                    icon: Download,
                  },
                  {
                    format: 'png_zip' as const,
                    label: '分页 ZIP',
                    description: '按页高切成多张 PNG',
                    icon: Files,
                  },
                  {
                    format: 'production_json' as const,
                    label: '制作资料 JSON',
                    description: '分镜与文案元数据',
                    icon: FileJson,
                  },
                ] as const
              ).map((item) => (
                <button
                  key={item.format}
                  type="button"
                  role="menuitem"
                  className="flex w-full items-start gap-2 rounded-sm px-2 py-2 text-left text-sm hover:bg-accent disabled:opacity-50"
                  disabled={exporting}
                  onClick={() => {
                    setExportOpen(false)
                    void handleExport(item.format)
                  }}
                >
                  <item.icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0">
                    <span className="block font-medium">{item.label}</span>
                    <span className="block text-xs text-muted-foreground">{item.description}</span>
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <Button
          size="icon-sm"
          className="ml-1 md:h-8 md:w-auto md:px-2.5"
          aria-label="生成分镜脚本"
          title="根据本话故事生成或重写分镜脚本（不是出图）"
          onClick={handleGenerate}
          disabled={storyBusy}
        >
          {storyBusy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
          <span className="hidden md:inline">{storyBusy ? '脚本生成中…' : '生成分镜脚本'}</span>
        </Button>
        <div className="mx-1 h-5 w-px bg-border" aria-hidden />
        <AccountMenu />
      </div>

      <RegenerateConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={() => {
          setConfirmOpen(false)
          void generateFromStory({ regenerateCharacters: false })
        }}
      />
    </header>
  )
}
