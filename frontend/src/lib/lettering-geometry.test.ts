import { describe, expect, it } from 'vitest'
import { clampLetteringPosition, clientDeltaToPct } from './lettering-geometry'

describe('clampLetteringPosition', () => {
  it('keeps the box inside the slot', () => {
    expect(clampLetteringPosition(-10, -5, 60)).toEqual({ x_pct: 0, y_pct: 0 })
    expect(clampLetteringPosition(80, 99, 60)).toEqual({ x_pct: 40, y_pct: 92 })
  })
})

describe('clientDeltaToPct', () => {
  it('maps pixels to percent of slot size', () => {
    expect(clientDeltaToPct(50, 25, 500, 250)).toEqual({ dx: 10, dy: 10 })
    expect(clientDeltaToPct(10, 10, 0, 100)).toEqual({ dx: 0, dy: 0 })
  })
})
