'use client'

import Image from '@/components/ui/image'
import { ArrowRight, CheckCircle2, CircleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ASSET_SOURCE_SHORT } from '@/lib/asset-labels'
import { useStudio } from './studio-provider'
import { FieldLabel } from './shared'
import { toast } from 'sonner'

export function SceneBoard() {
  const { project, dispatch, setStage } = useStudio()

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">场景资产</h1>
          <p className="mt-1 text-sm text-muted-foreground">分镜中复用的环境设定与氛围参考。</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" disabled={project.scenes.length === 0 || project.scenes.every((scene) => scene.confirmed)} onClick={() => {
            project.scenes.forEach((scene) => dispatch({ type: 'updateScene', id: scene.id, patch: { confirmed: true } }))
            toast.success('场景设定已确认')
          }}>
            <CheckCircle2 data-icon="inline-start" />
            {project.scenes.length > 0 && project.scenes.every((scene) => scene.confirmed) ? '已全部确认' : '确认场景设定'}
          </Button>
          <Button variant="secondary" onClick={() => setStage('storyboard')}>
            下一步：分镜
            <ArrowRight data-icon="inline-end" />
          </Button>
        </div>
      </div>

      {project.scenes.length === 0 ? (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">暂无场景资产</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {project.scenes.map((scene) => {
            const id = (f: string) => `scene-${scene.id}-${f}`
            return (
              <article key={scene.id} className="overflow-hidden rounded-lg border bg-card" aria-label={scene.name}>
                <div className="relative aspect-video bg-muted">
                  <Image src={scene.imageUrl} alt={`${scene.name} 场景参考`} fill sizes="(min-width: 768px) 440px, 100vw" className="object-cover" />
                  <span className="absolute bottom-2 left-2 rounded bg-neutral-950/70 px-1.5 py-0.5 text-[10px] text-neutral-200 backdrop-blur">
                    {ASSET_SOURCE_SHORT[scene.imageSource]}
                  </span>
                </div>
                  <div className="flex flex-col gap-3 p-4">
                  <p className={`flex items-center gap-1 text-xs ${scene.confirmed ? 'text-success' : 'text-warning'}`}>
                    {scene.confirmed ? <CheckCircle2 className="size-3.5" /> : <CircleAlert className="size-3.5" />}
                    {scene.confirmed ? '已确认' : '待确认'} · 示例参考图
                  </p>
                  <div className="flex flex-col gap-1.5">
                    <FieldLabel htmlFor={id('name')}>场景名</FieldLabel>
                    <Input
                      id={id('name')}
                      value={scene.name}
                      onChange={(e) => dispatch({ type: 'updateScene', id: scene.id, patch: { name: e.target.value } })}
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <FieldLabel htmlFor={id('desc')}>描述</FieldLabel>
                    <Textarea
                      id={id('desc')}
                      rows={3}
                      value={scene.description}
                      onChange={(e) =>
                        dispatch({ type: 'updateScene', id: scene.id, patch: { description: e.target.value } })
                      }
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <FieldLabel htmlFor={id('mood')}>氛围</FieldLabel>
                    <Input
                      id={id('mood')}
                      value={scene.mood}
                      onChange={(e) => dispatch({ type: 'updateScene', id: scene.id, patch: { mood: e.target.value } })}
                    />
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
