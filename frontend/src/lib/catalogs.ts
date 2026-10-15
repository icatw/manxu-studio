/** Single source for studio select options (not closed API enums). */

export const GENRES = ['玄幻', '都市', '悬疑', '科幻', '末日'] as const
export const VISUAL_STYLES = ['国风玄幻', '电影感写实', '日系漫画', '赛博朋克'] as const
export const AUDIENCES = ['青少年', '年轻成人', '全年龄', '女性向', '男性向'] as const
export const PANEL_COUNTS = [2, 4, 6, 8, 10] as const
export const ASPECT_RATIOS = ['16:9', '4:3', '1:1', '3:4'] as const

export type GenreOption = (typeof GENRES)[number]
export type VisualStyleOption = (typeof VISUAL_STYLES)[number]
export type AudienceOption = (typeof AUDIENCES)[number]
export type PanelCountOption = (typeof PANEL_COUNTS)[number]
export type AspectRatioOption = (typeof ASPECT_RATIOS)[number]

export const ASPECT_RATIO_VALUES: Record<AspectRatioOption, number> = {
  '16:9': 16 / 9,
  '4:3': 4 / 3,
  '1:1': 1,
  '3:4': 3 / 4,
}
