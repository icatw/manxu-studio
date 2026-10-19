/** Shared SERIAL-03 / F05 continue-next frontier for overview and studio. */

export type EpisodeFrontierItem = {
  id: string
  title: string
  summary?: string | null
}

export type ContinueNextDecision =
  | { kind: 'stay'; episodeId: string; toast: string }
  | { kind: 'studio'; episodeId: string; toast: string }
  | { kind: 'create_next' }

/** First episode without a non-empty summary is the continuity frontier. */
export function resolveContinueNext(episodes: EpisodeFrontierItem[]): ContinueNextDecision {
  const frontierIdx = episodes.findIndex((episode) => !(episode.summary ?? '').trim())
  if (frontierIdx === 0) {
    const first = episodes[0]!
    return {
      kind: 'stay',
      episodeId: first.id,
      toast: `请先为「${first.title}」生成摘要，再续写下一话`,
    }
  }
  if (frontierIdx > 0) {
    const target = episodes[frontierIdx]!
    return {
      kind: 'studio',
      episodeId: target.id,
      toast: `已打开「${target.title}」；该话尚无摘要，可先出分镜或稍后补摘要`,
    }
  }
  return { kind: 'create_next' }
}
