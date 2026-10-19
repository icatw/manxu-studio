/** Rule-based lettering layout templates for the current panel (LETTER-08). */

import { clampLetteringPosition } from '@/lib/lettering-geometry'
import type { LetteringObject, LetteringObjectPatch } from '@/services/layout-api'

export type LetteringLayoutTemplate = 'top_band' | 'dialogue_lr' | 'bottom_bar'

export const LETTERING_LAYOUT_TEMPLATES: {
  id: LetteringLayoutTemplate
  label: string
  hint: string
}[] = [
  { id: 'top_band', label: '顶栏', hint: '竖条顶区纵向叠放' },
  { id: 'dialogue_lr', label: '左右对谈', hint: '奇偶左右错开' },
  { id: 'bottom_bar', label: '底部条', hint: '贴底纵向排列' },
]

function widthForText(text: string): number {
  const length = text.trim().length
  // Keep in sync with backend width_pct_for_text (LETTER craft).
  return Math.max(48, Math.min(84, 36 + 0.7 * length))
}

function fontForText(text: string): LetteringObject['font_size'] {
  const length = text.trim().length
  if (length < 12) return 'lg'
  if (length > 48) return 'sm'
  return 'md'
}

function sortedItems(items: LetteringObject[]): LetteringObject[] {
  return [...items].sort((a, b) => a.position - b.position || a.id.localeCompare(b.id))
}

/** Compute geometry patches for a template; does not mutate text or kind. */
export function layoutPatchesForTemplate(
  items: LetteringObject[],
  template: LetteringLayoutTemplate,
): { id: string; patch: LetteringObjectPatch }[] {
  const ordered = sortedItems(items)
  if (ordered.length === 0) return []

  return ordered.map((item, index) => {
    const width_pct = widthForText(item.text)
    let x = 20
    let y = 5
    let tail: LetteringObject['tail'] = 'none'

    if (template === 'top_band') {
      x = 20
      y = Math.min(68, 5 + index * 16)
      tail = 'none'
    } else if (template === 'dialogue_lr') {
      const left = index % 2 === 0
      x = left ? 8 : 48
      y = Math.min(70, 8 + index * 14)
      tail = left ? 'bottom_left' : 'bottom_right'
    } else {
      // bottom_bar: stack upward so first line still reads higher
      const fromBottom = ordered.length - 1 - index
      y = Math.max(8, Math.min(88, 78 - fromBottom * 14))
      x = 12
      tail = 'none'
    }

    const clamped = clampLetteringPosition(x, y, width_pct)
    const patch: LetteringObjectPatch = {
      x_pct: clamped.x_pct,
      y_pct: clamped.y_pct,
      width_pct,
      font_size: fontForText(item.text),
      tail,
    }
    return { id: item.id, patch }
  })
}
