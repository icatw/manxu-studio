import { describe, expect, it } from 'vitest'
import { resolveContinueNext } from './episode-frontier'

describe('resolveContinueNext', () => {
  it('stays on first episode when it has no summary', () => {
    const result = resolveContinueNext([
      { id: 'ep1', title: '第一话', summary: '' },
      { id: 'ep2', title: '第二话', summary: '' },
    ])
    expect(result).toEqual({
      kind: 'stay',
      episodeId: 'ep1',
      toast: '请先为「第一话」生成摘要，再续写下一话',
    })
  })

  it('opens the first later shell without summary', () => {
    const result = resolveContinueNext([
      { id: 'ep1', title: '第一话', summary: '开场结束' },
      { id: 'ep2', title: '第二话', summary: '   ' },
      { id: 'ep3', title: '第三话', summary: '' },
    ])
    expect(result).toEqual({
      kind: 'studio',
      episodeId: 'ep2',
      toast: '已打开「第二话」；该话尚无摘要，可先出分镜或稍后补摘要',
    })
  })

  it('creates next only when every episode has a summary', () => {
    const result = resolveContinueNext([
      { id: 'ep1', title: '第一话', summary: '开场' },
      { id: 'ep2', title: '第二话', summary: '中段' },
    ])
    expect(result).toEqual({ kind: 'create_next' })
  })
})
