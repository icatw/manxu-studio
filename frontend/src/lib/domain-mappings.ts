import type { AspectRatio, ShotType } from '@/types/storyboard'

/** Map free-text shot labels from models/API into UI shot types. */
export function shotLabelToType(shot: string): ShotType {
  const normalized = shot.trim()
  if (normalized.includes('远景')) return 'wide'
  if (normalized.includes('大特写') || normalized.includes('极端特写')) return 'extreme-close-up'
  if (normalized.includes('特写')) return 'close-up'
  return 'medium'
}

export function shotTypeToLabel(shotType: ShotType): string {
  switch (shotType) {
    case 'wide':
      return '远景'
    case 'close-up':
      return '特写'
    case 'extreme-close-up':
      return '大特写'
    default:
      return '中景'
  }
}

export type ApiAspectRatio = 'portrait' | 'landscape' | 'square'

export function aspectRatioToApi(aspectRatio: AspectRatio | string): ApiAspectRatio {
  if (aspectRatio === '1:1') return 'square'
  if (aspectRatio === '3:4') return 'portrait'
  return 'landscape'
}

export function aspectRatioFromApi(aspectRatio: ApiAspectRatio): AspectRatio {
  if (aspectRatio === 'portrait') return '3:4'
  if (aspectRatio === 'square') return '1:1'
  return '16:9'
}
