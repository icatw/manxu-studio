'use client'

import Image from '@/components/ui/image'
import { AlertTriangle, Check, Info, Loader2, RefreshCw, Sparkles, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { ASSET_SOURCE_LABELS } from '@/lib/asset-labels'
import { cn } from '@/lib/utils'
import {
  ASPECT_RATIOS,
  SHOT_TYPE_LABELS,
  SHOT_TYPES,
  type AspectRatio,
  type ShotType,
  type StoryboardPanel,
} from '@/types/storyboard'
import { useStudio } from './studio-provider'
import { FieldLabel, StatusBadge } from './shared'

const SHOT_ITEMS = SHOT_TYPES.map((value) => ({ value, label: SHOT_TYPE_LABELS[value] }))
const ASPECT_ITEMS = ASPECT_RATIOS.map((value) => ({ value, label: value }))

export function PanelInspector() {
  const { project, selectedPanelId, stage, versions, selectImageVersion, dispatch } = useStudio()
  const panel = project.panels.find((p) => p.id === selectedPanelId)

  return (
    <aside className="flex h-[38dvh] w-full shrink-0 flex-col border-t bg-sidebar lg:h-full lg:min-h-0 lg:w-80 lg:border-l lg:border-t-0" aria-label="属性面板">
      <div className="flex h-11 shrink-0 items-center justify-between border-b px-4">
        <h2 className="text-sm font-semibold">
          {stage === 'storyboard' && panel ? `第 ${panel.panelNumber} 格` : '属性'}
        </h2>
        {stage === 'storyboard' && panel && <StatusBadge status={panel.status} progress={panel.progress} />}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        {stage === 'storyboard' && panel ? <PanelFields panel={panel} /> : <StageHelp />}
        {stage === 'storyboard' && panel && <PanelReview panel={panel} versions={versions[panel.id] ?? []} onSelectVersion={(id) => void selectImageVersion(panel.id, id)} onReview={(reviewStatus) => dispatch({ type: 'updatePanel', id: panel.id, patch: { reviewStatus } })} />}
      </ScrollArea>
    </aside>
  )
}

function PanelReview({ panel, versions, onSelectVersion, onReview }: {
  panel: StoryboardPanel
  versions: { id: string; image_url: string; is_current: boolean; created_at: string }[]
  onSelectVersion: (id: string) => void
  onReview: (status: 'draft' | 'in_review' | 'approved') => void
}) {
  return (
    <div className="flex flex-col gap-3 border-t p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium">审阅状态</span>
        <select aria-label="分镜审阅状态" className="h-8 max-w-36 rounded-md border bg-background px-2 text-xs" value={panel.reviewStatus ?? 'draft'} onChange={(event) => onReview(event.target.value as 'draft' | 'in_review' | 'approved')}>
          <option value="draft">草稿</option><option value="in_review">待审核</option><option value="approved">已通过</option>
        </select>
      </div>
      {versions.length > 0 && <section aria-label="图像版本" className="flex flex-col gap-2">
        <h3 className="text-xs font-medium">图像版本 · {versions.length}</h3>
        <div className="grid grid-cols-3 gap-2">
          {versions.map((version, index) => <button key={version.id} type="button" aria-label={`选择图像版本 ${index + 1}${version.is_current ? '，当前版本' : ''}`} aria-pressed={version.is_current} onClick={() => onSelectVersion(version.id)} className={`relative aspect-square overflow-hidden rounded border ${version.is_current ? 'border-primary ring-1 ring-primary' : 'border-border'}`}>
            <img src={version.image_url} alt={`分镜图像版本 ${index + 1}`} className="size-full object-cover" />
            <span className="absolute inset-x-0 bottom-0 bg-black/70 px-1 py-0.5 text-[10px] text-white">V{versions.length - index}{version.is_current ? ' · 当前' : ''}</span>
          </button>)}
        </div>
      </section>}
    </div>
  )
}

function StageHelp() {
  const { stage, project, generation } = useStudio()
  const tips: Record<typeof stage, string> = {
    story: '填写标题、梗概、题材与画风，然后生成角色设定与分镜脚本。重新生成分镜会删除旧分镜及其图像版本。',
    characters: '角色设定会写入每一格的画面提示词。修改后请重新确认，确保多格画面中的角色保持一致。',
    scenes: '场景资产定义分镜环境与氛围；可在场景资产页生成并维护参考图。',
    storyboard: '在画布中选择一格分镜以编辑镜头、对白与画面提示词。',
  }
  const confirmed = project.characters.filter((c) => c.confirmed).length
  return (
    <div className="flex flex-col gap-4 p-4 text-sm">
      <p className="leading-relaxed text-muted-foreground">{tips[stage]}</p>
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md bg-muted/60 p-2.5">
          <dt className="text-muted-foreground">角色确认</dt>
          <dd className="mt-1 font-medium tabular-nums">
            {confirmed}/{project.characters.length}
          </dd>
        </div>
        <div className="rounded-md bg-muted/60 p-2.5">
          <dt className="text-muted-foreground">分镜</dt>
          <dd className="mt-1 font-medium tabular-nums">{project.panels.length} 格</dd>
        </div>
      </dl>
      <DemoNotice providerName={generation.providerName} />
    </div>
  )
}

function DemoNotice({ providerName }: { providerName: string }) {
  if (!providerName.startsWith('演示')) return null
  return (
    <div className="flex gap-2 rounded-md border border-warning/25 bg-warning/5 p-3 text-xs leading-relaxed text-muted-foreground">
      <Info className="mt-0.5 size-3.5 shrink-0 text-warning" aria-hidden />
      <p>
        当前使用 <span className="text-foreground">{providerName}</span>，返回的是本地示例图片，并非真实 AI
        生成。接入服务端图像接口后即可替换。
      </p>
    </div>
  )
}

function PanelFields({ panel }: { panel: StoryboardPanel }) {
  const { project, dispatch, generation } = useStudio()
  const update = (patch: Partial<StoryboardPanel>) => dispatch({ type: 'updatePanel', id: panel.id, patch })
  const id = (field: string) => `panel-${panel.id}-${field}`
  const generating = panel.status === 'generating'

  return (
    <div className="flex flex-col gap-5 p-4">
      <section className="flex flex-col gap-2" aria-label="画面生成">
        {generating ? (
          <div className="flex flex-col gap-2 rounded-md bg-primary/10 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-primary">
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
                正在生成画面
              </span>
              <span className="tabular-nums text-muted-foreground">{panel.progress}%</span>
            </div>
            <Progress value={panel.progress} aria-label="生成进度" />
            <Button variant="outline" size="sm" onClick={() => generation.cancelPanel(panel.id)}>
              <Square data-icon="inline-start" />
              停止跟踪
            </Button>
          </div>
        ) : panel.status === 'failed' ? (
          <div className="flex flex-col gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3">
            <p className="flex items-start gap-1.5 text-xs text-destructive">
              <AlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden />
              {panel.errorMessage ?? '生成失败'}
            </p>
            <Button size="sm" onClick={() => void generation.generateOne(panel.id)}>
              <RefreshCw data-icon="inline-start" />
              重试
            </Button>
          </div>
        ) : (
          <Button onClick={() => void generation.generateOne(panel.id)}>
            {panel.imageUrl ? <RefreshCw data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
            {panel.imageUrl ? '重新生成本格画面' : '生成本格画面'}
          </Button>
        )}
        {panel.imageSource && panel.imageUrl && (
          <p className="text-[11px] text-muted-foreground">
            当前画面：{ASSET_SOURCE_LABELS[panel.imageSource]}
            {panel.generatedAt && ` · ${new Date(panel.generatedAt).toLocaleTimeString('zh-CN')}`}
          </p>
        )}
      </section>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <FieldLabel>镜头</FieldLabel>
          <Select
            items={SHOT_ITEMS}
            value={panel.shotType}
            onValueChange={(value) => value && update({ shotType: value as ShotType })}
          >
            <SelectTrigger className="w-full" aria-label="镜头类型">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SHOT_ITEMS.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <FieldLabel>画幅</FieldLabel>
          <Select
            items={ASPECT_ITEMS}
            value={panel.aspectRatio}
            onValueChange={(value) => value && update({ aspectRatio: value as AspectRatio })}
          >
            <SelectTrigger className="w-full" aria-label="画幅比例">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ASPECT_ITEMS.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('dialogue')} hint={`${panel.dialogue.length}/60`}>
          对白
        </FieldLabel>
        <Textarea
          id={id('dialogue')}
          value={panel.dialogue}
          maxLength={60}
          rows={2}
          onChange={(e) => update({ dialogue: e.target.value })}
          placeholder="留空则不显示对白气泡"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('scene')}>场景描述</FieldLabel>
        <Textarea id={id('scene')} value={panel.scene} rows={3} onChange={(e) => update({ scene: e.target.value })} />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('action')}>角色动作</FieldLabel>
        <Textarea id={id('action')} value={panel.action} rows={2} onChange={(e) => update({ action: e.target.value })} />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('composition')}>构图描述</FieldLabel>
        <Textarea
          id={id('composition')}
          value={panel.composition ?? ''}
          rows={2}
          onChange={(e) => update({ composition: e.target.value })}
          placeholder="镜头构图、主体位置与画面层次"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('storyPurpose')}>剧情作用</FieldLabel>
        <Textarea
          id={id('storyPurpose')}
          value={panel.storyPurpose ?? ''}
          rows={2}
          onChange={(e) => update({ storyPurpose: e.target.value })}
          placeholder="这一格在叙事中推进什么"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('emotion')}>情绪</FieldLabel>
        <Input id={id('emotion')} value={panel.emotion} onChange={(e) => update({ emotion: e.target.value })} />
      </div>

      <fieldset className="flex flex-col gap-1.5">
        <legend className="mb-1.5 text-xs font-medium text-muted-foreground">出场角色</legend>
        <div className="flex flex-wrap gap-1.5">
          {project.characters.map((character) => {
            const on = panel.characterIds.includes(character.id)
            return (
              <button
                key={character.id}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  update({
                    characterIds: on
                      ? panel.characterIds.filter((cid) => cid !== character.id)
                      : [...panel.characterIds, character.id],
                  })
                }
                className={cn(
                  'flex h-7 items-center gap-1.5 rounded-full border pr-2.5 pl-0.5 text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
                  on ? 'border-primary/50 bg-primary/15 text-foreground' : 'text-muted-foreground hover:bg-muted',
                )}
              >
                <span className="relative size-6 overflow-hidden rounded-full bg-muted">
                  <Image src={character.referenceImageUrl} alt="" fill sizes="24px" className="object-cover" />
                </span>
                {character.name}
                {on && <Check className="size-3 text-primary" aria-hidden />}
              </button>
            )
          })}
        </div>
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor={id('prompt')} hint="含角色一致性约束">
          画面提示词
        </FieldLabel>
        <Textarea
          id={id('prompt')}
          value={panel.imagePrompt}
          rows={7}
          className="font-mono text-xs leading-relaxed"
          onChange={(e) => update({ imagePrompt: e.target.value })}
        />
      </div>

      <DemoNotice providerName={generation.providerName} />
    </div>
  )
}
