'use client'

import { useMemo, useState } from 'react'
import Image from '@/components/ui/image'
import { ImageOff, Loader2, MessageSquareText, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { DialogueFallbackBubble, LetteringOverlay } from '@/components/series/lettering-overlay'
import { useEpisodeLayoutLettering } from '@/hooks/use-episode-layout-lettering'
import { cn } from '@/lib/utils'
import { ASPECT_RATIO_VALUES } from '@/types/storyboard'
import type { LetteringObject } from '@/services/layout-api'
import { useStudio } from './studio-provider'
import { RegenerateConfirmDialog } from './regenerate-confirm-dialog'

const STUB_SPEECH = '（填写对白）'
const STUB_NARRATION = '（填写旁白）'

export function ComicPreviewDialog() {
  const { project, previewOpen, setPreviewOpen, episodeId } = useStudio()
  const lettering = useEpisodeLayoutLettering(previewOpen ? episodeId : undefined)
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null)
  const [selectedLetteringId, setSelectedLetteringId] = useState<string | null>(null)
  const [replaceConfirmOpen, setReplaceConfirmOpen] = useState(false)

  const missing = project.panels.filter((p) => !p.imageUrl).length
  const selectedPanel =
    project.panels.find((panel) => panel.id === selectedPanelId) ?? project.panels[0] ?? null
  const binding = selectedPanel ? lettering.byPanelId.get(selectedPanel.id) : undefined
  const selectedLettering =
    (binding?.lettering ?? []).find((item) => item.id === selectedLetteringId) ?? null

  const letteredCount = useMemo(() => {
    let count = 0
    for (const panel of project.panels) {
      if ((lettering.byPanelId.get(panel.id)?.lettering.length ?? 0) > 0) count += 1
    }
    return count
  }, [lettering.byPanelId, project.panels])

  return (
    <>
    <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
      <DialogContent className="max-h-[92vh] gap-3 sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{project.title || '未命名作品'}</DialogTitle>
          <DialogDescription>
            制作预览 · 字效主编辑 · {project.panels.length} 格
            {missing > 0 ? ` · ${missing} 格尚未出图` : ''}
            {letteredCount > 0 ? ` · ${letteredCount} 格已有字效` : ''}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={lettering.busy || project.panels.length === 0}
            onClick={() => lettering.seed.mutate(false)}
          >
            {lettering.seed.isPending ? (
              <Loader2 data-icon="inline-start" className="animate-spin" />
            ) : (
              <MessageSquareText data-icon="inline-start" />
            )}
            从分镜生成气泡
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={lettering.busy || project.panels.length === 0 || letteredCount === 0}
            onClick={() => setReplaceConfirmOpen(true)}
          >
            替换已有
          </Button>
          <p className="text-xs text-muted-foreground">
            默认跳过已有字效的格；要覆盖占位气泡用「替换已有」。改字不重绘底图。
          </p>
        </div>

        <div className="grid min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
          <ScrollArea className="max-h-[60vh] rounded-md">
            <div className="flex flex-col gap-3 bg-neutral-100 p-4">
              {project.panels.map((panel, index) => {
                const panelBinding = lettering.byPanelId.get(panel.id)
                const items = panelBinding?.lettering ?? []
                const active = selectedPanel?.id === panel.id
                return (
                  <figure
                    key={panel.id}
                    className={cn(
                      'relative overflow-hidden border-[3px] border-neutral-900 bg-neutral-200',
                      active && 'ring-2 ring-primary ring-offset-2',
                    )}
                    style={{ aspectRatio: ASPECT_RATIO_VALUES[panel.aspectRatio] }}
                    onClick={() => {
                      setSelectedPanelId(panel.id)
                      setSelectedLetteringId(items[0]?.id ?? null)
                    }}
                  >
                    {panel.imageUrl ? (
                      <Image
                        src={panel.imageUrl}
                        alt={`第 ${panel.panelNumber} 格：${panel.scene}`}
                        fill
                        sizes="640px"
                        className="object-cover"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-neutral-500">
                        <ImageOff className="size-6" aria-label="尚未生成画面" />
                      </div>
                    )}
                    {items.length > 0 ? (
                      <LetteringOverlay
                        items={items}
                        interactive
                        draggable
                        selectedId={selectedLetteringId}
                        onSelect={(id) => {
                          setSelectedPanelId(panel.id)
                          setSelectedLetteringId(id)
                        }}
                        onPositionCommit={(id, position) => {
                          lettering.patch.mutate({
                            letteringId: id,
                            body: position,
                          })
                        }}
                      />
                    ) : (
                      <DialogueFallbackBubble text={panel.dialogue} alignRight={index % 2 === 1} />
                    )}
                  </figure>
                )
              })}
            </div>
          </ScrollArea>

          <aside className="space-y-3 rounded-lg border p-3 text-sm">
            <div>
              <h3 className="font-medium">字效</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                {selectedPanel
                  ? `第 ${selectedPanel.panelNumber} 格 · 可拖动气泡改位置`
                  : '选中一格后编辑气泡/旁白'}
              </p>
            </div>

            {selectedPanel && binding ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={lettering.busy}
                    onClick={() =>
                      lettering.create.mutate(
                        {
                          slotId: binding.slotId,
                          body: {
                            kind: 'speech_bubble',
                            text: STUB_SPEECH,
                            x_pct: 8,
                            y_pct: 6,
                            width_pct: 60,
                            tail: 'bottom_left',
                            font_size: 'md',
                          },
                        },
                        {
                          onSuccess: (row) => setSelectedLetteringId(row.id),
                        },
                      )
                    }
                  >
                    <Plus data-icon="inline-start" />
                    气泡
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={lettering.busy}
                    onClick={() =>
                      lettering.create.mutate(
                        {
                          slotId: binding.slotId,
                          body: {
                            kind: 'narration',
                            text: STUB_NARRATION,
                            x_pct: 8,
                            y_pct: 78,
                            width_pct: 84,
                            tail: 'none',
                            font_size: 'md',
                          },
                        },
                        {
                          onSuccess: (row) => setSelectedLetteringId(row.id),
                        },
                      )
                    }
                  >
                    <Plus data-icon="inline-start" />
                    旁白
                  </Button>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  新增气泡/旁白先写入占位文案，请改成定稿；不会自动复制整段分镜对白。多人台词请用「从分镜生成气泡」拆分。
                </p>

                <ul className="flex flex-col gap-1">
                  {binding.lettering.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={cn(
                          'w-full truncate rounded-md px-2 py-1.5 text-left text-xs',
                          selectedLetteringId === item.id
                            ? 'bg-sidebar-accent'
                            : 'hover:bg-muted/60',
                        )}
                        onClick={() => setSelectedLetteringId(item.id)}
                      >
                        {item.kind === 'speech_bubble' ? '气泡' : '旁白'} · {item.text}
                      </button>
                    </li>
                  ))}
                  {binding.lettering.length === 0 ? (
                    <li className="text-xs text-muted-foreground">本格尚无字效 · 可用上方生成或新增</li>
                  ) : null}
                </ul>

                {selectedLettering ? (
                  <LetteringEditor
                    item={selectedLettering}
                    busy={lettering.busy}
                    onPatch={(body) =>
                      lettering.patch.mutate({ letteringId: selectedLettering.id, body })
                    }
                    onDelete={() => {
                      lettering.remove.mutate(selectedLettering.id)
                      setSelectedLetteringId(null)
                    }}
                  />
                ) : null}
              </div>
            ) : selectedPanel && !binding ? (
              <p className="text-xs text-muted-foreground">
                本话尚无竖条布局。点「从分镜生成气泡」会自动生成默认页并种气泡。
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">先选中一格。</p>
            )}
          </aside>
        </div>
      </DialogContent>
    </Dialog>

    <RegenerateConfirmDialog
      open={replaceConfirmOpen}
      onOpenChange={setReplaceConfirmOpen}
      title="用分镜对白替换已有字效？"
      description="将清空本话各槽现有气泡/旁白，再按分镜对白重新生成默认气泡。已手工改过的字效会丢失，此操作不可撤销。"
      confirmLabel="替换并生成"
      onConfirm={() => {
        setReplaceConfirmOpen(false)
        lettering.seed.mutate(true)
      }}
    />
    </>
  )
}

function LetteringEditor({
  item,
  busy,
  onPatch,
  onDelete,
}: {
  item: LetteringObject
  busy: boolean
  onPatch: (body: {
    text?: string
    x_pct?: number
    y_pct?: number
    width_pct?: number
    font_size?: LetteringObject['font_size']
  }) => void
  onDelete: () => void
}) {
  return (
    <div className="space-y-2 border-t pt-3">
      <label className="grid gap-1 text-xs">
        <span className="text-muted-foreground">文案</span>
        <Textarea
          key={`${item.id}-text`}
          defaultValue={item.text}
          rows={3}
          disabled={busy}
          onBlur={(event) => {
            const value = event.target.value.trim()
            if (!value || value === item.text) return
            onPatch({ text: value })
          }}
        />
      </label>
      <div className="grid grid-cols-3 gap-2">
        {(
          [
            ['x_pct', 'X%', item.x_pct],
            ['y_pct', 'Y%', item.y_pct],
            ['width_pct', '宽%', item.width_pct],
          ] as const
        ).map(([field, label, current]) => (
          <label key={field} className="grid gap-1 text-xs">
            <span className="text-muted-foreground">{label}</span>
            <Input
              type="number"
              min={field === 'width_pct' ? 10 : 0}
              max={100}
              defaultValue={current}
              key={`${item.id}-${field}-${current}`}
              disabled={busy}
              onBlur={(event) => {
                const value = Number(event.target.value)
                if (!Number.isFinite(value) || value === current) return
                onPatch({ [field]: value })
              }}
            />
          </label>
        ))}
      </div>
      <label className="grid gap-1 text-xs">
        <span className="text-muted-foreground">字号</span>
        <select
          className="h-8 rounded-md border bg-background px-2"
          value={item.font_size}
          disabled={busy}
          onChange={(event) =>
            onPatch({ font_size: event.target.value as LetteringObject['font_size'] })
          }
        >
          <option value="sm">小</option>
          <option value="md">中</option>
          <option value="lg">大</option>
        </select>
      </label>
      <Button size="sm" variant="ghost" className="text-destructive" disabled={busy} onClick={onDelete}>
        <Trash2 data-icon="inline-start" />
        删除字效
      </Button>
    </div>
  )
}
