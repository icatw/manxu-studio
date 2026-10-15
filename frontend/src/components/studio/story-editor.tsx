'use client'

import { useState } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { AUDIENCES, GENRES, PANEL_COUNTS, VISUAL_STYLES, type StoryIdea } from '@/types/story'
import { useStudio } from './studio-provider'
import { FieldLabel } from './shared'
import { RegenerateConfirmDialog } from './regenerate-confirm-dialog'

function ChipGroup<T extends string | number>({
  label,
  options,
  value,
  onChange,
  format = String,
}: {
  label: string
  options: readonly T[]
  value: T
  onChange: (value: T) => void
  format?: (value: T) => string
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-xs font-medium text-muted-foreground">{label}</legend>
      <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={label}>
        {options.map((option) => {
          const active = option === value
          return (
            <button
              key={String(option)}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(option)}
              className={cn(
                'h-8 rounded-md border px-3 text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
                active
                  ? 'border-primary bg-primary/15 text-foreground'
                  : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              {format(option)}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

export function StoryEditor() {
  const { project, dispatch, storyBusy, generateFromStory } = useStudio()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const { story } = project
  const update = (patch: Partial<StoryIdea>) => dispatch({ type: 'updateStory', patch })
  const synopsisEmpty = !story.synopsis.trim()

  const handleGenerate = () => {
    if (synopsisEmpty) return
    if (project.panels.length > 0) setConfirmOpen(true)
    else void generateFromStory({ regenerateCharacters: true })
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">故事创意</h1>
        <p className="mt-1 text-sm text-muted-foreground">根据故事生成 AI 角色设定、场景和分镜脚本，确认后可继续逐格出图。</p>
      </div>

      <div className="flex flex-col gap-5 rounded-lg border bg-card p-5">
        <div className="flex flex-col gap-1.5">
          <FieldLabel htmlFor="story-title">故事标题</FieldLabel>
          <Input
            id="story-title"
            value={story.title}
            maxLength={40}
            onChange={(e) => update({ title: e.target.value })}
            placeholder="例如：超时订单"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <FieldLabel htmlFor="story-synopsis" hint={`${story.synopsis.length}/300`}>
            故事梗概
          </FieldLabel>
          <Textarea
            id="story-synopsis"
            value={story.synopsis}
            maxLength={300}
            rows={4}
            onChange={(e) => update({ synopsis: e.target.value })}
            placeholder="描述主角、冲突与转折……"
            aria-invalid={synopsisEmpty || undefined}
          />
          {synopsisEmpty && <p className="text-xs text-destructive">请填写故事梗概后再生成</p>}
        </div>

        <ChipGroup label="题材" options={GENRES} value={story.genre} onChange={(genre) => update({ genre })} />
        <ChipGroup label="画风" options={VISUAL_STYLES} value={story.style} onChange={(style) => update({ style })} />
        <ChipGroup
          label="目标读者"
          options={AUDIENCES}
          value={story.audience}
          onChange={(audience) => update({ audience })}
        />
        <ChipGroup
          label="分镜数量"
          options={PANEL_COUNTS}
          value={story.panelCount}
          onChange={(panelCount) => update({ panelCount })}
          format={(n) => `${n} 格`}
        />
      </div>

      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-muted-foreground">AI 将生成角色文字设定与参考图、场景资产和 {story.panelCount} 格分镜脚本。</p>
        <Button onClick={handleGenerate} disabled={storyBusy || synopsisEmpty}>
          {storyBusy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
          {storyBusy ? '生成中…' : '生成角色与分镜'}
        </Button>
      </div>

      <RegenerateConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="重新生成分镜脚本？"
        description="现有分镜及其图像版本会被删除并替换；角色和场景资产会保留。此操作不可撤销。"
        confirmLabel="替换分镜脚本"
        onConfirm={() => {
          setConfirmOpen(false)
          void generateFromStory({ regenerateCharacters: true })
        }}
      />
    </div>
  )
}
