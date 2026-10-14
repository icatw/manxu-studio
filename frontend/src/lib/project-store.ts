import type { Character } from '@/types/character'
import type { SceneAsset, StoryIdea } from '@/types/story'
import { SHOT_TYPES, ASPECT_RATIOS, type ComicProject, type StoryboardPanel } from '@/types/storyboard'

export type ProjectAction =
  | { type: 'hydrate'; project: ComicProject }
  | { type: 'reset'; project: ComicProject }
  | { type: 'setTitle'; title: string }
  | { type: 'updateStory'; patch: Partial<StoryIdea> }
  | { type: 'updateCharacter'; id: string; patch: Partial<Character> }
  | { type: 'confirmCharacters' }
  | { type: 'updateScene'; id: string; patch: Partial<SceneAsset> }
  | { type: 'applyGenerated'; characters: Character[]; scenes: SceneAsset[]; panels: StoryboardPanel[] }
  | { type: 'setPanels'; panels: StoryboardPanel[] }
  | { type: 'updatePanel'; id: string; patch: Partial<StoryboardPanel> }
  | { type: 'movePanel'; id: string; direction: -1 | 1 }
  | { type: 'clearPanels' }
  /** Transient generation status/progress — not recorded in undo history. */
  | { type: 'panelRuntime'; id: string; patch: Partial<StoryboardPanel> }
  | { type: 'panelGenerated'; id: string; patch: Partial<StoryboardPanel> }
  | { type: 'replacePanelId'; id: string; nextId: string }
  | { type: 'undo' }
  | { type: 'redo' }

export interface HistoryState {
  past: ComicProject[]
  present: ComicProject
  future: ComicProject[]
  lastKey: string | null
  lastTime: number
  revision: number
}

const HISTORY_LIMIT = 60
const COALESCE_MS = 1000

function renumber(panels: StoryboardPanel[]) {
  return panels.map((p, i) => (p.panelNumber === i + 1 ? p : { ...p, panelNumber: i + 1 }))
}

function patchPanel(project: ComicProject, id: string, patch: Partial<StoryboardPanel>): ComicProject {
  return {
    ...project,
    panels: project.panels.map((p) => (p.id === id ? { ...p, ...patch } : p)),
  }
}

function settleRuntime(project: ComicProject): ComicProject {
  return {
    ...project,
    panels: project.panels.map((p) =>
      p.status === 'generating'
        ? { ...p, status: p.imageUrl ? 'completed' : 'draft', progress: p.imageUrl ? 100 : 0 }
        : p,
    ),
  }
}

function applyContent(project: ComicProject, action: ProjectAction): ComicProject {
  switch (action.type) {
    case 'setTitle':
      return { ...project, title: action.title }
    case 'updateStory':
      return { ...project, story: { ...project.story, ...action.patch } }
    case 'updateCharacter':
      return {
        ...project,
        characters: project.characters.map((c) =>
          c.id === action.id ? { ...c, ...action.patch, confirmed: action.patch.confirmed ?? false } : c,
        ),
      }
    case 'confirmCharacters':
      return { ...project, characters: project.characters.map((c) => ({ ...c, confirmed: true })) }
    case 'updateScene':
      return {
        ...project,
        scenes: project.scenes.map((s) => (s.id === action.id ? { ...s, ...action.patch, confirmed: action.patch.confirmed ?? false } : s)),
      }
    case 'applyGenerated':
      return {
        ...project,
        characters: action.characters,
        scenes: action.scenes,
        panels: renumber(action.panels),
      }
    case 'setPanels':
      return { ...project, panels: renumber(action.panels) }
    case 'updatePanel':
    case 'panelGenerated':
      return patchPanel(project, action.id, action.patch)
    case 'replacePanelId':
      return {
        ...project,
        panels: project.panels.map((panel) =>
          panel.id === action.id ? { ...panel, id: action.nextId } : panel,
        ),
      }
    case 'movePanel': {
      const index = project.panels.findIndex((p) => p.id === action.id)
      const target = index + action.direction
      if (index < 0 || target < 0 || target >= project.panels.length) return project
      const panels = [...project.panels]
      ;[panels[index], panels[target]] = [panels[target], panels[index]]
      return { ...project, panels: renumber(panels) }
    }
    case 'clearPanels':
      return { ...project, panels: [] }
    default:
      return project
  }
}

function coalesceKey(action: ProjectAction): string | null {
  switch (action.type) {
    case 'setTitle':
      return 'title'
    case 'updateStory':
      return `story:${Object.keys(action.patch).join(',')}`
    case 'updateCharacter':
      return `char:${action.id}:${Object.keys(action.patch).join(',')}`
    case 'updateScene':
      return `scene:${action.id}:${Object.keys(action.patch).join(',')}`
    case 'updatePanel':
      return `panel:${action.id}:${Object.keys(action.patch).join(',')}`
    default:
      return null
  }
}

export function createHistory(project: ComicProject): HistoryState {
  return { past: [], present: project, future: [], lastKey: null, lastTime: 0, revision: 0 }
}

export function historyReducer(state: HistoryState, action: ProjectAction): HistoryState {
  switch (action.type) {
    case 'hydrate':
      return createHistory(action.project)
    case 'reset':
      return {
        ...state,
        past: [...state.past, state.present].slice(-HISTORY_LIMIT),
        present: action.project,
        future: [],
        lastKey: null,
        revision: state.revision + 1,
      }
    case 'panelRuntime':
      return { ...state, present: patchPanel(state.present, action.id, action.patch) }
    case 'undo': {
      if (state.past.length === 0) return state
      const previous = settleRuntime(state.past[state.past.length - 1])
      return {
        ...state,
        past: state.past.slice(0, -1),
        present: previous,
        future: [state.present, ...state.future],
        lastKey: null,
        revision: state.revision + 1,
      }
    }
    case 'redo': {
      if (state.future.length === 0) return state
      const [next, ...rest] = state.future
      return {
        ...state,
        past: [...state.past, state.present].slice(-HISTORY_LIMIT),
        present: settleRuntime(next),
        future: rest,
        lastKey: null,
        revision: state.revision + 1,
      }
    }
    default: {
      const next = applyContent(state.present, action)
      if (next === state.present) return state
      const present = { ...next, updatedAt: new Date().toISOString() }
      const key = coalesceKey(action)
      const now = Date.now()
      const shouldCoalesce = key !== null && key === state.lastKey && now - state.lastTime < COALESCE_MS
      return {
        past: shouldCoalesce ? state.past : [...state.past, state.present].slice(-HISTORY_LIMIT),
        present,
        future: [],
        lastKey: key,
        lastTime: now,
        revision: state.revision + 1,
      }
    }
  }
}

/* ---------- Persistence ---------- */

export const STORAGE_KEY = 'manxu-studio:project:v1'

const isString = (v: unknown): v is string => typeof v === 'string'
const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

function sanitizePanel(raw: unknown): StoryboardPanel | null {
  if (!isObject(raw)) return null
  const required = ['id', 'scene', 'action', 'emotion', 'dialogue', 'imagePrompt', 'demoAssetUrl']
  if (!required.every((k) => isString(raw[k]))) return null
  const shotType = SHOT_TYPES.includes(raw.shotType as never) ? (raw.shotType as StoryboardPanel['shotType']) : 'medium'
  const aspectRatio = ASPECT_RATIOS.includes(raw.aspectRatio as never)
    ? (raw.aspectRatio as StoryboardPanel['aspectRatio'])
    : '4:3'
  const imageUrl = isString(raw.imageUrl) ? raw.imageUrl : null
  const rawStatus = raw.status
  const status: StoryboardPanel['status'] =
    rawStatus === 'completed' || rawStatus === 'failed' || rawStatus === 'draft'
      ? rawStatus
      : imageUrl
        ? 'completed'
        : 'draft'
  const imageSource =
    raw.imageSource === 'example' || raw.imageSource === 'demo' || raw.imageSource === 'ai'
      ? raw.imageSource
      : null
  return {
    id: raw.id as string,
    panelNumber: 0,
    shotType,
    scene: raw.scene as string,
    action: raw.action as string,
    emotion: raw.emotion as string,
    dialogue: raw.dialogue as string,
    imagePrompt: raw.imagePrompt as string,
    characterIds: Array.isArray(raw.characterIds) ? raw.characterIds.filter(isString) : [],
    aspectRatio,
    imageUrl,
    imageSource: imageUrl ? imageSource : null,
    demoAssetUrl: raw.demoAssetUrl as string,
    status: status === 'completed' && !imageUrl ? 'draft' : status,
    progress: status === 'completed' ? 100 : 0,
    errorMessage: isString(raw.errorMessage) ? raw.errorMessage : null,
    generatedAt: isString(raw.generatedAt) ? raw.generatedAt : null,
  }
}

export function parseStoredProject(json: string | null, fallback: ComicProject): ComicProject | null {
  if (!json) return null
  try {
    const raw: unknown = JSON.parse(json)
    if (!isObject(raw) || !isString(raw.id) || !isString(raw.title)) return null
    if (!isObject(raw.story) || !Array.isArray(raw.panels) || !Array.isArray(raw.characters)) return null

    const story = { ...fallback.story, ...(raw.story as Partial<StoryIdea>) }
    const characters = (raw.characters as unknown[])
      .filter((c): c is Character => isObject(c) && isString(c.id) && isString(c.name))
      .map((c) => ({ ...fallback.characters[0], ...c }))
    const scenes = Array.isArray(raw.scenes)
      ? (raw.scenes as unknown[]).filter((s): s is SceneAsset => isObject(s) && isString(s.id) && isString(s.imageUrl))
      : fallback.scenes
    const panels = renumber(
      (raw.panels as unknown[]).map(sanitizePanel).filter((p): p is StoryboardPanel => p !== null),
    )

    return {
      id: raw.id,
      title: raw.title,
      story,
      characters: characters.length ? characters : fallback.characters,
      scenes,
      panels,
      updatedAt: isString(raw.updatedAt) ? raw.updatedAt : new Date().toISOString(),
    }
  } catch {
    return null
  }
}
