import { describe, expect, it } from 'vitest'
import { mergeHydratedProject } from '@/lib/project-store'
import type { ComicProject, StoryboardPanel } from '@/types/storyboard'

function panel(partial: Partial<StoryboardPanel> & { id: string }): StoryboardPanel {
  return {
    panelNumber: 1,
    shotType: 'medium',
    scene: 'scene',
    action: 'action',
    emotion: '',
    dialogue: '',
    imagePrompt: 'prompt',
    characterIds: [],
    aspectRatio: '4:3',
    imageUrl: null,
    imageSource: null,
    status: 'draft',
    progress: 0,
    errorMessage: null,
    generatedAt: null,
    ...partial,
  }
}

function project(panels: StoryboardPanel[], title = 'Story'): ComicProject {
  return {
    id: 'ep-1',
    title,
    story: {
      title,
      synopsis: 'synopsis',
      genre: '玄幻',
      style: '日系漫画',
      audience: '年轻成人',
      panelCount: 4,
      aspectRatio: '16:9',
    },
    characters: [],
    scenes: [],
    panels,
    updatedAt: '2026-10-15T00:00:00.000Z',
  }
}

describe('mergeHydratedProject', () => {
  it('returns server project when clean and idle', () => {
    const current = project([panel({ id: 'p1', scene: 'local' })])
    const server = project([panel({ id: 'p1', scene: 'server', status: 'completed', imageUrl: '/a.png' })])
    expect(mergeHydratedProject(current, server, { dirty: false, busyPanelIds: new Set() })).toBe(server)
  })

  it('keeps generating runtime while taking server content when not dirty', () => {
    const current = project([
      panel({ id: 'p1', status: 'generating', progress: 42, scene: 'old', imageUrl: null }),
    ])
    const server = project([
      panel({ id: 'p1', status: 'draft', progress: 0, scene: 'server', imageUrl: null }),
    ])
    const merged = mergeHydratedProject(current, server, {
      dirty: false,
      busyPanelIds: new Set(['p1']),
    })
    expect(merged.panels[0]).toMatchObject({
      scene: 'server',
      status: 'generating',
      progress: 42,
    })
  })

  it('preserves dirty panel text and adopts non-busy server images', () => {
    const current = project([
      panel({ id: 'p1', scene: 'edited', status: 'draft', imageUrl: null }),
      panel({ id: 'p2', scene: 'editing-busy', status: 'generating', progress: 20, imageUrl: null }),
    ])
    const server = project([
      panel({
        id: 'p1',
        scene: 'server',
        status: 'completed',
        imageUrl: '/done.png',
        imageSource: 'ai',
        progress: 100,
      }),
      panel({ id: 'p2', scene: 'server-busy', status: 'draft', progress: 0, imageUrl: null }),
    ])
    const merged = mergeHydratedProject(current, server, {
      dirty: true,
      busyPanelIds: new Set(['p2']),
    })
    expect(merged.panels[0]).toMatchObject({
      scene: 'edited',
      imageUrl: '/done.png',
      status: 'completed',
    })
    expect(merged.panels[1]).toMatchObject({
      scene: 'editing-busy',
      status: 'generating',
      progress: 20,
    })
  })
})
