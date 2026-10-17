/** Clamp lettering box so it stays mostly inside the slot (LETTER-06). */

export function clampLetteringPosition(
  xPct: number,
  yPct: number,
  widthPct: number,
): { x_pct: number; y_pct: number } {
  const width = Math.min(100, Math.max(10, widthPct))
  const maxX = Math.max(0, 100 - width)
  const x_pct = Math.min(maxX, Math.max(0, xPct))
  const y_pct = Math.min(92, Math.max(0, yPct))
  return {
    x_pct: Math.round(x_pct * 10) / 10,
    y_pct: Math.round(y_pct * 10) / 10,
  }
}

export function clientDeltaToPct(
  deltaX: number,
  deltaY: number,
  slotWidthPx: number,
  slotHeightPx: number,
): { dx: number; dy: number } {
  if (slotWidthPx <= 0 || slotHeightPx <= 0) return { dx: 0, dy: 0 }
  return {
    dx: (deltaX / slotWidthPx) * 100,
    dy: (deltaY / slotHeightPx) * 100,
  }
}
