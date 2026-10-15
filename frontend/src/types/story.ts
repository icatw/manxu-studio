export const GENRES = ['玄幻', '都市', '悬疑', '科幻', '末日'] as const
export type Genre = (typeof GENRES)[number]

export const VISUAL_STYLES = ['国风玄幻', '电影感写实', '日系漫画', '赛博朋克'] as const
export type VisualStyle = (typeof VISUAL_STYLES)[number]

export const AUDIENCES = ['青少年', '年轻成人', '全年龄', '女性向', '男性向'] as const
export type Audience = (typeof AUDIENCES)[number]

export const PANEL_COUNTS = [2, 4, 6, 8, 10] as const
export type PanelCount = (typeof PANEL_COUNTS)[number]

export interface StoryIdea {
  title: string
  synopsis: string
  genre: Genre
  style: VisualStyle
  audience: Audience
  panelCount: PanelCount
  aspectRatio?: '16:9' | '4:3' | '1:1' | '3:4'
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
