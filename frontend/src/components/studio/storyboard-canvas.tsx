'use client'

import { useState } from 'react'
import { Clapperboard, Loader2, Plus, Sparkles, Square, Trash2, Wand2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useStudio } from './studio-provider'
import { StoryboardPanelCard } from './storyboard-panel'
import { RegenerateConfirmDialog } from './regenerate-confirm-dialog'

export function StoryboardCanvas() {
  const { project, dispatch, selectedPanelId, selectPanel, generation, storyBusy, generateFromStory, setStage } =
    useStudio()
  const { addPanel, removePanel } = useStudio()
  const [confirmAll, setConfirmAll] = useState(false)
  const { panels } = project
  const completedWithImages = panels.filter((p) => p.imageUrl).length

  const startBatch = () => {
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
          <h2 className="text-base font-semibold">还没有分镜</h2>
          <p className="mt-1 text-sm text-muted-foreground">先完善故事创意，再一键生成分镜脚本。</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setStage('story')}>
            编辑故事
          </Button>
          <Button onClick={() => void generateFromStory({ regenerateCharacters: false })} disabled={storyBusy}>
            {storyBusy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
            生成分镜
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
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
              取消全部
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={startBatch} disabled={storyBusy}>
              <Wand2 data-icon="inline-start" />
              全部生成画面
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {panels.map((panel, index) => (
          <StoryboardPanelCard
            key={panel.id}
            panel={panel}
            index={index}
            total={panels.length}
            selected={panel.id === selectedPanelId}
            onSelect={() => selectPanel(panel.id)}
            onMove={(direction) => dispatch({ type: 'movePanel', id: panel.id, direction })}
            onGenerate={() => {
              selectPanel(panel.id)
              void generation.generateOne(panel.id)
            }}
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
    </div>
  )
}
