'use client'

import Image from '@/components/ui/image'
import { ArrowRight, CheckCircle2, CircleAlert, Lock, LockOpen, UserRound } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ASSET_SOURCE_SHORT } from '@/lib/asset-labels'
import type { Character, CharacterEditableField } from '@/types/character'
import { useStudio } from './studio-provider'
import { FieldLabel } from './shared'

const FIELDS: { key: CharacterEditableField; label: string; multiline?: boolean }[] = [
  { key: 'role', label: '身份定位' },
  { key: 'appearance', label: '外貌', multiline: true },
  { key: 'hairstyle', label: '发型' },
  { key: 'clothing', label: '服装', multiline: true },
  { key: 'signatureTraits', label: '标志性特征' },
  { key: 'personality', label: '性格' },
]

function CharacterCard({ character }: { character: Character }) {
  const { dispatch } = useStudio()
  const id = (field: string) => `char-${character.id}-${field}`
  const update = (patch: Partial<Character>) => dispatch({ type: 'updateCharacter', id: character.id, patch })

  return (
    <article className="flex flex-col overflow-hidden rounded-lg border bg-card sm:flex-row" aria-label={character.name}>
      <div className="relative aspect-square w-full shrink-0 bg-muted sm:w-48">
        {character.referenceImageUrl ? (
          <Image
            src={character.referenceImageUrl}
            alt={`${character.name} AI 角色参考图`}
            fill
            sizes="(min-width: 640px) 192px, 100vw"
            className="object-cover"
          />
        ) : (
          <div className="absolute inset-0 grid place-items-center text-muted-foreground">
            <UserRound className="size-12" aria-hidden />
          </div>
        )}
        <span className="absolute right-2 top-2 rounded bg-neutral-950/70 px-2 py-1 text-[10px] text-neutral-100">
          {character.referenceLocked
            ? '定妆已锁定'
            : character.referenceImageUrl
              ? ASSET_SOURCE_SHORT.ai
              : '暂无 AI 参考图'}
        </span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor={id('name')} className="sr-only">
            角色名
          </label>
          <Input
            id={id('name')}
            value={character.name}
            maxLength={16}
            onChange={(e) => update({ name: e.target.value })}
            className="h-8 max-w-48 font-semibold"
          />
          <span className="rounded border px-2 py-1 text-[11px] text-muted-foreground">
            {character.generationSource === 'ai' ? 'AI 起稿' : '手动设定'}
          </span>
          {character.confirmed ? (
            <span className="flex items-center gap-1 text-xs text-success">
              <CheckCircle2 className="size-3.5" aria-hidden />
              已确认
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-warning">
              <CircleAlert className="size-3.5" aria-hidden />
              待确认
            </span>
          )}
          <Button
            type="button"
            variant={character.referenceLocked ? 'secondary' : 'outline'}
            size="sm"
            disabled={!character.referenceImageUrl && !character.referenceLocked}
            title={
              character.referenceLocked
                ? '已锁定：重新生成角色草稿时会保留这张定妆照'
                : '锁定后，重新生成角色草稿不会替换这张参考图，分镜出图会附带一致性约束'
            }
            onClick={() => {
              if (!character.referenceImageUrl && !character.referenceLocked) {
                toast.error('请先生成角色参考图再锁定')
                return
              }
              const next = !character.referenceLocked
              update({ referenceLocked: next })
              toast.success(next ? '定妆照已锁定' : '已解除定妆锁定')
            }}
          >
            {character.referenceLocked ? <Lock data-icon="inline-start" /> : <LockOpen data-icon="inline-start" />}
            {character.referenceLocked ? '已锁定' : '锁定定妆'}
          </Button>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {FIELDS.map(({ key, label, multiline }) => (
            <div key={key} className={multiline ? 'flex flex-col gap-1.5 md:col-span-2' : 'flex flex-col gap-1.5'}>
              <FieldLabel htmlFor={id(key)}>{label}</FieldLabel>
              {multiline ? (
                <Textarea
                  id={id(key)}
                  value={character[key]}
                  rows={2}
                  onChange={(e) => update({ [key]: e.target.value })}
                />
              ) : (
                <Input id={id(key)} value={character[key]} onChange={(e) => update({ [key]: e.target.value })} />
              )}
            </div>
          ))}
        </div>
      </div>
    </article>
  )
}

export function CharacterBoard() {
  const { project, dispatch, setStage } = useStudio()
  const allConfirmed = project.characters.every((c) => c.confirmed)

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">角色资产</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            这些设定会作为一致性约束写入每格画面的提示词。修改后需重新确认。
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={allConfirmed ? 'outline' : 'default'}
            disabled={allConfirmed}
            onClick={() => {
              dispatch({ type: 'confirmCharacters' })
              toast.success('角色设定已确认')
            }}
          >
            <CheckCircle2 data-icon="inline-start" />
            {allConfirmed ? '已全部确认' : '确认角色设定'}
          </Button>
          <Button variant="secondary" onClick={() => setStage('scenes')}>
            下一步：场景
            <ArrowRight data-icon="inline-end" />
          </Button>
        </div>
      </div>
      <div className="flex flex-col gap-4">
        {project.characters.map((character) => (
          <CharacterCard key={character.id} character={character} />
        ))}
      </div>
    </div>
  )
}
