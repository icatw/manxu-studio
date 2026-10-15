export {
  AUDIENCES,
  GENRES,
  PANEL_COUNTS,
  VISUAL_STYLES,
  type AudienceOption,
  type GenreOption,
  type PanelCountOption,
  type VisualStyleOption,
} from '@/lib/catalogs'

import type { AspectRatioOption, PanelCountOption } from '@/lib/catalogs'

/** Runtime story fields are free strings from the API; option types remain for selects. */
export type Genre = string
export type VisualStyle = string
export type Audience = string
export type PanelCount = PanelCountOption | number

export interface StoryIdea {
  title: string
  synopsis: string
  genre: Genre
  style: VisualStyle
  audience: Audience
  panelCount: PanelCount
  aspectRatio?: AspectRatioOption
}

export type AssetSource = 'example' | 'demo' | 'ai'

export interface SceneAsset {
  id: string
  name: string
  description: string
  mood: string
  imageUrl: string
  imageSource: AssetSource | null
  confirmed?: boolean
}
