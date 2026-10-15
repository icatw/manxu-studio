import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type RefObject,
  type SetStateAction,
} from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api/client'
import { aspectRatioToApi } from '@/lib/domain-mappings'
import { mergeHydratedProject, type ProjectAction } from '@/lib/project-store'
import { toCharacterPatch, toComicProject, toPanelPatch, toScenePatch, type WorkspaceData } from '@/services/workspace-api'
import type { ComicProject } from '@/types/storyboard'

export type SaveState = 'idle' | 'saving' | 'saved' | 'error'

export function comparable(project: ComicProject) {
  return JSON.stringify({
    title: project.title,
    story: project.story,
    characters: project.characters.map(toCharacterPatch),
    scenes: project.scenes.map(toScenePatch),
    panels: project.panels.map((panel) => ({ id: panel.id, ...toPanelPatch(panel) })),
  })
}

export async function expectNoError(error: unknown, data?: unknown) {
  if (error || data === undefined) {
    const detail =
      typeof error === 'object' && error !== null && 'detail' in error
        ? String((error as { detail: unknown }).detail)
        : 'API 保存失败，请检查服务后重试'
    throw new Error(detail)
  }
}

export async function persistProject(
  current: ComicProject,
  previous: ComicProject,
  projectId: string,
  episodeId: string,
) {
  const projectPatch: Record<string, string> = {}
  if (current.title !== previous.title) projectPatch.title = current.title
  if (current.story.synopsis !== previous.story.synopsis) projectPatch.synopsis = current.story.synopsis
  if (current.story.genre !== previous.story.genre) projectPatch.genre = current.story.genre
  if (current.story.style !== previous.story.style) projectPatch.art_style = current.story.style
  const aspectRatio = current.story.aspectRatio ?? '16:9'
  const previousAspectRatio = previous.story.aspectRatio ?? '16:9'
  if (aspectRatio !== previousAspectRatio) {
    projectPatch.aspect_ratio = aspectRatioToApi(aspectRatio)
  }
  if (Object.keys(projectPatch).length) {
    const { data, error } = await api.PATCH('/projects/{project_id}', {
      params: { path: { project_id: projectId } },
      body: projectPatch,
    })
    await expectNoError(error, data)
  }

  const episodePatch: Record<string, string | number> = {}
  if (current.story.title !== previous.story.title) episodePatch.title = current.story.title
  if (current.story.synopsis !== previous.story.synopsis) episodePatch.synopsis = current.story.synopsis
  if (current.story.panelCount !== previous.story.panelCount) episodePatch.panel_count = current.story.panelCount
  if (Object.keys(episodePatch).length) {
    const { data, error } = await api.PATCH('/episodes/{episode_id}', {
      params: { path: { episode_id: episodeId } },
      body: episodePatch,
    })
    await expectNoError(error, data)
  }

  const previousCharacters = new Map(previous.characters.map((item) => [item.id, item]))
  for (const character of current.characters) {
    const before = previousCharacters.get(character.id)
    if (!before || JSON.stringify(toCharacterPatch(before)) === JSON.stringify(toCharacterPatch(character))) continue
    const { data, error } = await api.PATCH('/characters/{character_id}', {
      params: { path: { character_id: character.id } },
      body: toCharacterPatch(character),
    })
    await expectNoError(error, data)
  }

  const previousScenes = new Map(previous.scenes.map((item) => [item.id, item]))
  for (const scene of current.scenes) {
    const before = previousScenes.get(scene.id)
    if (!before || JSON.stringify(toScenePatch(before)) === JSON.stringify(toScenePatch(scene))) continue
    const { data, error } = await api.PATCH('/scenes/{scene_id}', {
      params: { path: { scene_id: scene.id } },
      body: toScenePatch(scene),
    })
    await expectNoError(error, data)
  }

  const previousPanels = new Map(previous.panels.map((item) => [item.id, item]))
  const currentPanels = new Map(current.panels.map((item) => [item.id, item]))
  for (const panel of previous.panels) {
    if (currentPanels.has(panel.id)) continue
    const { error } = await api.DELETE('/panels/{panel_id}', { params: { path: { panel_id: panel.id } } })
    if (error) throw new Error('删除分镜失败，请重试')
  }
  for (const panel of current.panels) {
    const before = previousPanels.get(panel.id)
    if (!before) {
      const { data, error } = await api.POST('/episodes/{episode_id}/panels', {
        params: { path: { episode_id: episodeId } },
        body: { id: panel.id, ...toPanelPatch(panel) },
      })
      await expectNoError(error, data)
      continue
    }
    if (JSON.stringify(toPanelPatch(before)) === JSON.stringify(toPanelPatch(panel))) continue
    const { data, error } = await api.PATCH('/panels/{panel_id}', {
      params: { path: { panel_id: panel.id } },
      body: toPanelPatch(panel),
    })
    await expectNoError(error, data)
  }
  const previousOrder = previous.panels.map((panel) => panel.id)
  const currentOrder = current.panels.map((panel) => panel.id)
  if (currentOrder.length && JSON.stringify(previousOrder) !== JSON.stringify(currentOrder)) {
    const { data, error } = await api.PUT('/episodes/{episode_id}/panels/order', {
      params: { path: { episode_id: episodeId } },
      body: { panel_ids: currentOrder },
    })
    await expectNoError(error, data)
  }
}

export function useStudioHydrate({
  workspace,
  projectRef,
  getBusyPanelIds,
  dispatch,
  setSelectedPanelId,
  setSaveState,
  setLastSavedAt,
  baselineRef,
  lastSignatureRef,
}: {
  workspace: WorkspaceData
  projectRef: RefObject<ComicProject>
  getBusyPanelIds: () => ReadonlySet<string>
  dispatch: Dispatch<ProjectAction>
  setSelectedPanelId: Dispatch<SetStateAction<string | null>>
  setSaveState: (state: SaveState) => void
  setLastSavedAt: (date: Date | null) => void
  baselineRef: MutableRefObject<ComicProject>
  lastSignatureRef: MutableRefObject<string>
}) {
  const workspaceSignature = JSON.stringify(workspace)
  const signatureRef = useRef(workspaceSignature)

  useEffect(() => {
    if (workspaceSignature === signatureRef.current) return
    signatureRef.current = workspaceSignature
    const next = toComicProject(workspace)
    const current = projectRef.current
    const dirty = comparable(current) !== lastSignatureRef.current
    const busyPanelIds = new Set([
      ...getBusyPanelIds(),
      ...current.panels.filter((panel) => panel.status === 'generating').map((panel) => panel.id),
    ])
    const merged = mergeHydratedProject(current, next, { dirty, busyPanelIds })
    if (!dirty) {
      baselineRef.current = next
      lastSignatureRef.current = comparable(merged)
      setSaveState('saved')
      setLastSavedAt(new Date(workspace.episode.updated_at))
    }
    dispatch({ type: 'hydrate', project: merged })
    setSelectedPanelId((selected) =>
      selected && merged.panels.some((panel) => panel.id === selected)
        ? selected
        : (merged.panels[0]?.id ?? null),
    )
  }, [
    baselineRef,
    dispatch,
    getBusyPanelIds,
    lastSignatureRef,
    projectRef,
    setLastSavedAt,
    setSaveState,
    setSelectedPanelId,
    workspace,
    workspaceSignature,
  ])
}

export function useStudioAutosave({
  project,
  projectId,
  episodeId,
  initialSavedAt,
  baselineRef,
  lastSignatureRef,
}: {
  project: ComicProject
  projectId: string
  episodeId: string
  initialSavedAt: string
  baselineRef: MutableRefObject<ComicProject>
  lastSignatureRef: MutableRefObject<string>
}) {
  const [ready, setReady] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>('saved')
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(() => new Date(initialSavedAt))

  useEffect(() => {
    setReady(true)
  }, [])

  useEffect(() => {
    if (!ready) return
    const signature = comparable(project)
    if (signature === lastSignatureRef.current) return
    setSaveState('saving')
    const timer = window.setTimeout(async () => {
      try {
        await persistProject(project, baselineRef.current, projectId, episodeId)
        baselineRef.current = structuredClone(project)
        lastSignatureRef.current = signature
        setSaveState('saved')
        setLastSavedAt(new Date())
      } catch (error) {
        setSaveState('error')
        toast.error('保存失败', { description: error instanceof Error ? error.message : '请检查网络后重试' })
      }
    }, 650)
    return () => window.clearTimeout(timer)
  }, [baselineRef, episodeId, lastSignatureRef, project, projectId, ready])

  return { saveState, setSaveState, lastSavedAt, setLastSavedAt }
}
