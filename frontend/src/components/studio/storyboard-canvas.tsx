'use client'

import { useState } from 'react'
import { Clapperboard, Loader2, Plus, Sparkles, Square, Trash2, Wand2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { describeChangeImpact } from '@/lib/change-impact'
import { useEpisodeLayoutLettering } from '@/hooks/use-episode-layout-lettering'
import { useStudio } from './studio-provider'
import { StoryboardPanelCard } from './storyboard-panel'
import { RegenerateConfirmDialog } from './regenerate-confirm-dialog'

export function StoryboardCanvas() {
  const {
    project,
    dispatch,
    selectedPanelId,
    selectPanel,
    generation,
    storyBusy,
    generateFromStory,
    setStage,
    episodeId,
    changeImpact,
    dismissChangeImpact,
  } = useStudio()
  const { addPanel, removePanel } = useStudio()
  const lettering = useEpisodeLayoutLettering(episodeId)
  const impactCopy = changeImpact ? describeChangeImpact(changeImpact) : null
  const [confirmAll, setConfirmAll] = useState(false)
  const [trialOpen, setTrialOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<'one' | 'all' | null>(null)
  const [pendingPanelId, setPendingPanelId] = useState<string | null>(null)
  const { panels } = project
  const completedWithImages = panels.filter((p) => p.imageUrl).length
  const castCount = project.characters.length
  const lockedCount = project.characters.filter((c) => c.referenceLocked && c.referenceImageUrl).length
  const confirmedCount = project.characters.filter((c) => c.confirmed).length
  const needsCastGate = castCount === 0
  const softWarn = castCount > 0 && lockedCount === 0
  const needsScenesSoft = project.scenes.length === 0

  const requestGenerateOne = (panelId: string) => {
    selectPanel(panelId)
    if (needsCastGate) {
      setPendingPanelId(panelId)
      setPendingAction('one')
      setTrialOpen(true)
      return
    }
    void generation.generateOne(panelId)
  }

  const startBatch = () => {
    if (needsCastGate) {
      setPendingAction('all')
      setTrialOpen(true)
      return
    }
    if (completedWithImages > 0) setConfirmAll(true)
    else void generation.generateAll()
  }

  if (panels.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
          <Clapperboard className="size-6 text-muted-foreground" aria-hidden />
        </div>
        <div>
          <h2 className="text-base font-semibold">还没有分镜脚本</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            先完善本话梗概与角色，再生成分镜脚本（文本结构，不是出图）。
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setStage('story')}>
            编辑故事
          </Button>
          <Button onClick={() => void generateFromStory({ regenerateCharacters: false })} disabled={storyBusy}>
            {storyBusy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
            {storyBusy ? '生成中…' : '生成分镜脚本'}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-lg font-semibold tracking-tight">{project.story.title || '未命名故事'}</h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {project.story.genre} · {project.story.style} · {panels.length} 格 · 已出图 {completedWithImages}/
            {panels.length}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={addPanel}><Plus data-icon="inline-start" />添加分镜</Button>
          {selectedPanelId && <Button size="sm" variant="ghost" onClick={() => removePanel(selectedPanelId)} aria-label="删除所选分镜"><Trash2 data-icon="inline-start" />删除</Button>}
          {generation.batchRunning ? (
            <Button variant="outline" size="sm" onClick={generation.cancelAll}>
              <Square data-icon="inline-start" />
              停止全部跟踪
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={startBatch} disabled={storyBusy}>
              <Wand2 data-icon="inline-start" />
              全部生成画面
            </Button>
          )}
        </div>
      </div>

      {project.story.synopsis.trim() ? (
        <section className="rounded-lg border bg-card px-4 py-3">
          <h2 className="text-xs font-medium text-muted-foreground">本话梗概</h2>
          <p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap">{project.story.synopsis}</p>
        </section>
      ) : (
        <section className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm">
          本话梗概为空。建议先到「故事」补全冲突与转折，再批量出图。
          <Button size="sm" variant="link" className="ml-1 h-auto p-0" onClick={() => setStage('story')}>
            去编辑
          </Button>
        </section>
      )}

      {impactCopy ? (
        <section className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-medium">{impactCopy.title}</p>
              <p className="mt-1 text-muted-foreground">{impactCopy.description}</p>
            </div>
            <Button size="sm" variant="ghost" onClick={dismissChangeImpact}>
              知道了
            </Button>
          </div>
        </section>
      ) : null}

      {needsCastGate ? (
        <section className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm">
          <p className="font-medium">尚未建立角色</p>
          <p className="mt-1 text-muted-foreground">
            默认请先生成并确认角色（建议锁定定妆），再出图，以免整话换脸返工。若只想试构图，可在出图时确认「试画」。
          </p>
          <Button size="sm" className="mt-2" onClick={() => setStage('characters')}>
            去建立角色
          </Button>
        </section>
      ) : softWarn ? (
        <section className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm">
          <p className="font-medium">定妆尚未锁定</p>
          <p className="mt-1 text-muted-foreground">
            角色 {confirmedCount}/{castCount} 已确认 · 定妆锁定 {lockedCount}/{castCount}。未定妆时出图一致性较弱。
          </p>
          <Button size="sm" className="mt-2" variant="secondary" onClick={() => setStage('characters')}>
            去锁定定妆
          </Button>
        </section>
      ) : (
        <section className="rounded-lg border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
          角色就绪：已确认 {confirmedCount}/{castCount} · 定妆锁定 {lockedCount}/{castCount}
          <button
            type="button"
            className="ml-2 underline underline-offset-2 hover:text-foreground"
            onClick={() => setStage('characters')}
          >
            管理角色
          </button>
        </section>
      )}

      {needsScenesSoft ? (
        <section className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm">
          <p className="font-medium">尚无场景资产</p>
          <p className="mt-1 text-muted-foreground">
            环境一致性较弱。可按本话生成场景库；不影响继续出图。
          </p>
          <Button size="sm" className="mt-2" variant="secondary" onClick={() => setStage('scenes')}>
            去生成场景
          </Button>
        </section>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {panels.map((panel, index) => (
          <StoryboardPanelCard
            key={panel.id}
            panel={panel}
            index={index}
            total={panels.length}
            selected={panel.id === selectedPanelId}
            lettering={lettering.byPanelId.get(panel.id)?.lettering}
            onSelect={() => selectPanel(panel.id)}
            onMove={(direction) => dispatch({ type: 'movePanel', id: panel.id, direction })}
            onGenerate={() => requestGenerateOne(panel.id)}
            onCancel={() => generation.cancelPanel(panel.id)}
          />
        ))}
      </div>

      <RegenerateConfirmDialog
        open={confirmAll}
        onOpenChange={setConfirmAll}
        title="重新生成全部画面？"
        description={`将为全部 ${panels.length} 格创建新图像版本；已有 ${completedWithImages} 格的旧版本会保留，可稍后切换回去。`}
        confirmLabel="全部生成"
        onConfirm={() => {
          setConfirmAll(false)
          void generation.generateAll()
        }}
      />

      <RegenerateConfirmDialog
        open={trialOpen}
        onOpenChange={(open) => {
          setTrialOpen(open)
          if (!open) {
            setPendingAction(null)
            setPendingPanelId(null)
          }
        }}
        title="尚无角色，确认试画？"
        description="没有角色与定妆时生成的画面很难在后续保持一致，整话可能需要重绘。建议先去建立角色；若仍要试构图，请确认以试画继续。"
        confirmLabel="确认试画并出图"
        onConfirm={() => {
          const action = pendingAction
          const panelId = pendingPanelId
          setTrialOpen(false)
          setPendingAction(null)
          setPendingPanelId(null)
          if (action === 'all') void generation.generateAll({ acknowledgeTrial: true })
          else if (action === 'one' && panelId) void generation.generateOne(panelId, { acknowledgeTrial: true })
        }}
      />
    </div>
  )
}
