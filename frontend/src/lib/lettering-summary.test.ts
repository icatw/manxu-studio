import { describe, expect, it } from 'vitest'
import { dialogueDivergesFromLettering, letteringSummary } from './lettering-summary'
import type { LetteringObject } from '@/services/layout-api'

function bubble(text: string): LetteringObject {
  return {
    id: '1',
    slot_id: 's',
    kind: 'speech_bubble',
    text,
    x_pct: 8,
    y_pct: 6,
    width_pct: 60,
    tail: 'bottom_left',
    font_size: 'md',
    position: 0,
    created_at: '',
    updated_at: '',
  }
}

describe('letteringSummary', () => {
  it('joins multiple bubbles', () => {
    expect(letteringSummary([bubble('甲：你好'), bubble('乙：嗯')])).toBe('甲：你好 / 乙：嗯')
  })
})

describe('dialogueDivergesFromLettering', () => {
  it('detects divergence', () => {
    expect(dialogueDivergesFromLettering('旧脚本', [bubble('新字效')])).toBe(true)
    expect(dialogueDivergesFromLettering('同一句', [bubble('同一句')])).toBe(false)
    expect(dialogueDivergesFromLettering('任意', [])).toBe(false)
  })
})
