'use client'

import Image from '@/components/ui/image'
import { ImageIcon, ImageOff, Loader2, RefreshCw, Sparkles } from 'lucide-react'
import { ArrowRight, CheckCircle2, CircleAlert } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ASSET_SOURCE_SHORT } from '@/lib/asset-labels'
import { generateSceneReferences } from '@/services/workspace-api'
import { useStudio } from './studio-provider'
import { FieldLabel } from './shared'
import { RegenerateConfirmDialog } from './regenerate-confirm-dialog'

const TEXTAREA_CLASS = 'max-h-32 overflow-y-auto field-sizing-fixed'

export function SceneBoard() {
  const { project, dispatch, setStage, projectId, episodeId, refreshWorkspace } = useStudio()
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [rebuildOpen, setRebuildOpen] = useState(false)
  const missingReferences = project.scenes.filter((scene) => !scene.imageUrl).length
  const allConfirmed = project.scenes.length > 0 && project.scenes.every((scene) => scene.confirmed)
  const busy = busyKey !== null
  const synopsisEmpty = !project.story.synopsis.trim()

  async function runGeneration(
    key: string,
    action: () => Promise<{ warnings: string[] }>,
    successMessage: string,
  ) {
    setBusyKey(key)
    try {
      const { warnings } = await action()
      await refreshWorkspace()
      if (warnings.length) {
        toast.warning(successMessage, { description: warnings.join(' ') })
      } else {
        toast.success(successMessage)
      }
    } catch (error) {
      toast.error('场景生成失败', {
        description: error instanceof Error ? error.message : '请稍后重试',
      })
    } finally {
      setBusyKey(null)
    }
  }

  function requireSynopsis(): boolean {
    if (!synopsisEmpty) return true
    toast.error('请先填写故事梗概')
    setStage('story')
    return false
  }

  const draftGuidance = `本话梗概：${project.story.synopsis}`

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 p-6 pb-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">作品场景</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            全话共用的环境设定与氛围参考；各话分镜可引用此处场景。默认追加新人，不会清掉已有角色或分镜。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {project.scenes.length === 0 ? (
            <Button
              disabled={busy}
              onClick={() => {
                if (!requireSynopsis()) return
                void runGeneration(
                  'draft',
                  () =>
                    generateSceneReferences(projectId, {
                      episodeId,
                      imageOnly: false,
                      castMode: 'append',
                      guidance: draftGuidance,
                    }),
                  '场景设定已生成',
                )
              }}
            >
              {busyKey === 'draft' ? (
                <Loader2 className="animate-spin" data-icon="inline-start" />
              ) : (
                <Sparkles data-icon="inline-start" />
              )}
              {busyKey === 'draft' ? '生成中…' : '根据本话生成场景'}
            </Button>
          ) : (
            <>
              {missingReferences > 0 && (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() =>
                    void runGeneration(
                      'missing',
                      () =>
                        generateSceneReferences(projectId, {
                          episodeId,
                          imageOnly: true,
                        }),
                      '场景参考图已生成',
                    )
                  }
                >
                  {busyKey === 'missing' ? (
                    <Loader2 className="animate-spin" data-icon="inline-start" />
                  ) : (
                    <ImageIcon data-icon="inline-start" />
                  )}
                  {busyKey === 'missing' ? '正在生成参考图…' : `生成缺失参考图 (${missingReferences})`}
                </Button>
              )}
              <Button
                variant="outline"
                size="default"
                disabled={busy || synopsisEmpty}
                onClick={() => {
                  if (!requireSynopsis()) return
                  void runGeneration(
                    'append',
                    () =>
                      generateSceneReferences(projectId, {
                        episodeId,
                        imageOnly: false,
                        castMode: 'append',
                        guidance: draftGuidance,
                      }),
                    '已按本话补充场景',
                  )
                }}
              >
                {busyKey === 'append' ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : (
                  <Sparkles data-icon="inline-start" />
                )}
                {busyKey === 'append' ? '补充中…' : '为本话补充场景…'}
              </Button>
            </>
          )}
          <Button
            variant={allConfirmed ? 'outline' : project.scenes.length === 0 ? 'outline' : 'default'}
            disabled={project.scenes.length === 0 || allConfirmed}
            onClick={() => {
              project.scenes.forEach((scene) =>
                dispatch({ type: 'updateScene', id: scene.id, patch: { confirmed: true } }),
              )
              toast.success('场景设定已确认')
            }}
          >
            <CheckCircle2 data-icon="inline-start" />
            {allConfirmed ? '已全部确认' : '确认场景设定'}
          </Button>
          <Button variant="secondary" onClick={() => setStage('storyboard')}>
            {project.scenes.length === 0 ? '跳过，先看分镜' : '下一步：分镜'}
            <ArrowRight data-icon="inline-end" />
          </Button>
        </div>
      </div>

      {project.scenes.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-sm text-muted-foreground">暂无场景资产</p>
          <p className="mt-2 text-xs text-muted-foreground">
            可一键按本话梗概生成环境库；也可跳过，稍后再在分镜提示中补建。
          </p>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[11px] text-muted-foreground">只会追加新场景，不会改已有参考图。</p>
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              disabled={busy || synopsisEmpty}
              onClick={() => setRebuildOpen(true)}
            >
              重建作品场景库…
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {project.scenes.map((scene) => {
              const id = (f: string) => `scene-${scene.id}-${f}`
              return (
                <article key={scene.id} className="overflow-hidden rounded-lg border bg-card" aria-label={scene.name}>
                  <div className="relative aspect-video bg-muted">
                    {scene.imageUrl ? (
                      <>
                        <Image
                          src={scene.imageUrl}
                          alt={`${scene.name} AI 场景参考`}
                          fill
                          sizes="(min-width: 768px) 440px, 100vw"
                          className="object-cover"
                        />
                        <span className="absolute bottom-2 left-2 rounded bg-neutral-950/70 px-1.5 py-0.5 text-[10px] text-neutral-200 backdrop-blur">
                          {ASSET_SOURCE_SHORT.ai}
                        </span>
                      </>
                    ) : (
                      <div className="absolute inset-0 grid place-items-center text-muted-foreground">
                        <span className="flex items-center gap-2 text-xs">
                          <ImageOff className="size-4" aria-hidden />
                          暂无场景参考图
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-3 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p
                        className={`flex items-center gap-1 text-xs ${scene.confirmed ? 'text-success' : 'text-warning'}`}
                      >
                        {scene.confirmed ? <CheckCircle2 className="size-3.5" /> : <CircleAlert className="size-3.5" />}
                        {scene.confirmed ? '已确认' : '待确认'} · AI 文本设定
                      </p>
                      <div className="flex gap-1.5">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          onClick={() =>
                            void runGeneration(
                              scene.id,
                              () =>
                                generateSceneReferences(projectId, {
                                  episodeId,
                                  sceneIds: [scene.id],
                                  imageOnly: false,
                                }),
                              '场景设定已重生',
                            )
                          }
                        >
                          <RefreshCw data-icon="inline-start" />
                          重生设定
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          onClick={() =>
                            void runGeneration(
                              scene.id,
                              () =>
                                generateSceneReferences(projectId, {
                                  episodeId,
                                  sceneIds: [scene.id],
                                  imageOnly: true,
                                }),
                              '场景参考图已更新',
                            )
                          }
                        >
                          <ImageIcon data-icon="inline-start" />
                          重出参考图
                        </Button>
                      </div>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <FieldLabel htmlFor={id('name')}>场景名</FieldLabel>
                      <Input
                        id={id('name')}
                        value={scene.name}
                        onChange={(e) =>
                          dispatch({ type: 'updateScene', id: scene.id, patch: { name: e.target.value } })
                        }
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <FieldLabel htmlFor={id('desc')}>描述</FieldLabel>
                      <Textarea
                        id={id('desc')}
                        rows={3}
                        className={TEXTAREA_CLASS}
                        value={scene.description}
                        onChange={(e) =>
                          dispatch({
                            type: 'updateScene',
                            id: scene.id,
                            patch: { description: e.target.value },
                          })
                        }
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <FieldLabel htmlFor={id('mood')}>氛围</FieldLabel>
                      <Input
                        id={id('mood')}
                        value={scene.mood}
                        onChange={(e) =>
                          dispatch({ type: 'updateScene', id: scene.id, patch: { mood: e.target.value } })
                        }
                      />
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        </>
      )}

      <RegenerateConfirmDialog
        open={rebuildOpen}
        onOpenChange={setRebuildOpen}
        title="重建整部作品的场景库？"
        description="将按本话梗概重新生成场景并覆盖作品库，可能删除未再出现的场景，并清空分镜中失效的场景引用。此操作不可撤销。"
        confirmLabel="重建场景库"
        onConfirm={() => {
          setRebuildOpen(false)
          if (!requireSynopsis()) return
          void runGeneration(
            'rebuild',
            () =>
              generateSceneReferences(projectId, {
                episodeId,
                imageOnly: false,
                castMode: 'replace',
                guidance: draftGuidance,
              }),
            '作品场景库已重建',
          )
        }}
      />
    </div>
  )
}
