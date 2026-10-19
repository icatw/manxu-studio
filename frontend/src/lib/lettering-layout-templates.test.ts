import { describe, expect, it } from 'vitest'

import { layoutPatchesForTemplate } from '@/lib/lettering-layout-templates'
import type { LetteringObject } from '@/services/layout-api'

function bubble(partial: Partial<LetteringObject> & Pick<LetteringObject, 'id' | 'text' | 'position'>): LetteringObject {
  return {
    slot_id: 'slot-1',
    kind: 'speech_bubble',
    x_pct: 40,
    y_pct: 40,
    width_pct: 40,
    font_size: 'md',
    tail: 'none',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...partial,
  }
}

describe('layoutPatchesForTemplate', () => {
  it('returns empty for no items', () => {
    expect(layoutPatchesForTemplate([], 'top_band')).toEqual([])
  })

  it('top_band stacks vertically without tails', () => {
    const items = [
      bubble({ id: 'b', text: '第二', position: 1 }),
      bubble({ id: 'a', text: '第一句稍长一点', position: 0 }),
    ]
    const patches = layoutPatchesForTemplate(items, 'top_band')
    expect(patches.map((p) => p.id)).toEqual(['a', 'b'])
    expect(patches[0].patch.y_pct).toBeLessThan(patches[1].patch.y_pct!)
    expect(patches.every((p) => p.patch.tail === 'none')).toBe(true)
    expect(patches.every((p) => p.patch.x_pct === 20)).toBe(true)
  })

  it('dialogue_lr alternates left/right with tails', () => {
    const items = [
      bubble({ id: 'a', text: '左', position: 0 }),
      bubble({ id: 'b', text: '右', position: 1 }),
    ]
    const patches = layoutPatchesForTemplate(items, 'dialogue_lr')
    expect(patches[0].patch.x_pct).toBeLessThan(patches[1].patch.x_pct!)
    expect(patches[0].patch.tail).toBe('bottom_left')
    expect(patches[1].patch.tail).toBe('bottom_right')
  })

  it('bottom_bar keeps first item above later ones', () => {
    const items = [
      bubble({ id: 'a', text: '旁白一', position: 0 }),
      bubble({ id: 'b', text: '旁白二', position: 1 }),
      bubble({ id: 'c', text: '旁白三', position: 2 }),
    ]
    const patches = layoutPatchesForTemplate(items, 'bottom_bar')
    expect(patches[0].patch.y_pct!).toBeLessThan(patches[2].patch.y_pct!)
    expect(patches.every((p) => p.patch.tail === 'none')).toBe(true)
  })

  it('does not include text in patches', () => {
    const patches = layoutPatchesForTemplate(
      [bubble({ id: 'a', text: '勿改', position: 0 })],
      'top_band',
    )
    expect(patches[0].patch).not.toHaveProperty('text')
    expect(patches[0].patch).not.toHaveProperty('kind')
  })
})
