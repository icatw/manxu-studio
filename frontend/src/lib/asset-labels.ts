import type { AssetSource } from '@/types/story'

export const ASSET_SOURCE_LABELS: Record<AssetSource, string> = {
  example: '示例素材',
  demo: '演示占位 · 非 AI 生成',
  ai: 'AI 生成',
}

export const ASSET_SOURCE_SHORT: Record<AssetSource, string> = {
  example: '示例素材',
  demo: '演示占位',
  ai: 'AI 生成',
}
