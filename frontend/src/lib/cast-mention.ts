/** Detect cast names mentioned in panel text but not bound as 出场角色 (F04). */

export type NamedCast = { id: string; name: string }

function normalizeName(name: string) {
  return name.trim().toLocaleLowerCase().replace(/\s+/g, "")
}

export function mentionedCastNotBound(
  characters: NamedCast[],
  boundIds: string[],
  haystack: string,
): NamedCast[] {
  if (!characters.length || !haystack.trim()) return []
  const bound = new Set(boundIds)
  const text = haystack
  const normalizedText = normalizeName(haystack)
  const ordered = [...characters]
    .filter((character) => {
      const name = character.name.trim()
      if (!name) return false
      // Skip single Latin letters; allow CJK single-char names like「零」.
      if (name.length === 1 && /^[A-Za-z]$/.test(name)) return false
      return true
    })
    .sort((a, b) => b.name.trim().length - a.name.trim().length)

  const found: NamedCast[] = []
  const seen = new Set<string>()
  for (const character of ordered) {
    if (bound.has(character.id) || seen.has(character.id)) continue
    const name = character.name.trim()
    if (text.includes(name) || normalizedText.includes(normalizeName(name))) {
      found.push(character)
      seen.add(character.id)
    }
  }
  return found
}
