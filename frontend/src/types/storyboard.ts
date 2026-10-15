import {
  ASPECT_RATIOS,
  ASPECT_RATIO_VALUES,
  type AspectRatioOption,
} from '@/lib/catalogs'
import type { Character } from './character'
import type { AssetSource, SceneAsset, StoryIdea } from './story'

export const SHOT_TYPES = ['wide', 'medium', 'close-up', 'extreme-close-up'] as const
export type ShotType = (typeof SHOT_TYPES)[number]

export const SHOT_TYPE_LABELS: Record<ShotType, string> = {
  wide: '远景',
  medium: '中景',
  'close-up': '特写',
  'extreme-close-up': '大特写',
}

export { ASPECT_RATIOS, ASPECT_RATIO_VALUES }
export type AspectRatio = AspectRatioOption

export type PanelStatus = 'draft' | 'generating' | 'completed' | 'failed'

export const PANEL_STATUS_LABELS: Record<PanelStatus, string> = {
  draft: '草稿',
  generating: '生成中',
  completed: '已完成',
  failed: '失败',
}

export interface StoryboardPanel {
  id: string
  panelNumber: number
  shotType: ShotType
  scene: string
  action: string
  emotion: string
  dialogue: string
  imagePrompt: string
  characterIds: string[]
  aspectRatio: AspectRatio
  imageUrl: string | null
  imageSource: AssetSource | null
  status: PanelStatus
  progress: number
  errorMessage: string | null
  generatedAt: string | null
  reviewStatus?: 'draft' | 'in_review' | 'approved'
  composition?: string
  storyPurpose?: string
  sceneId?: string | null
}

export type PanelContentField =
  | 'shotType'
  | 'scene'
  | 'action'
  | 'emotion'
  | 'dialogue'
  | 'imagePrompt'
  | 'characterIds'
  | 'aspectRatio'
  | 'composition'
  | 'storyPurpose'

export type StudioStage = 'story' | 'characters' | 'scenes' | 'storyboard'

export interface ComicProject {
  id: string
  title: string
  story: StoryIdea
  characters: Character[]
  scenes: SceneAsset[]
  panels: StoryboardPanel[]
  updatedAt: string
}
