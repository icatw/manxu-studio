import type { LetteringObject } from '@/services/layout-api'

/** Join lettering bodies for list/inspector previews (LETTER-07). */
export function letteringSummary(items: LetteringObject[], maxLen = 80): string {
  const parts = items
    .map((item) => item.text.trim())
    .filter(Boolean)
  if (parts.length === 0) return ''
  const joined = parts.join(' / ')
  if (joined.length <= maxLen) return joined
  return `${joined.slice(0, Math.max(0, maxLen - 1))}…`
}

function normalizeScript(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

/** True when script dialogue and lettering bodies differ meaningfully. */
export function dialogueDivergesFromLettering(
  dialogue: string,
  items: LetteringObject[],
): boolean {
  if (items.length === 0) return false
  const lettering = normalizeScript(items.map((item) => item.text.trim()).filter(Boolean).join('\n'))
  const script = normalizeScript(dialogue)
  if (!lettering) return false
  return script !== lettering
}
