'use client'

import { useCallback, useEffect, useRef, useState, type Dispatch, type RefObject } from 'react'
import { toast } from 'sonner'
import type { ProjectAction } from '@/lib/project-store'
import { imageGenerationService, isAbortError, type ImageGenerationService } from '@/services/image-generation-service'
import { listActiveEpisodePanelTasks } from '@/services/workspace-api'
import type { ComicProject } from '@/types/storyboard'

interface Options {
  projectRef: RefObject<ComicProject>
  episodeId: string
  dispatch: Dispatch<ProjectAction>
  service?: ImageGenerationService
  concurrency?: number
  onGenerated?: () => void
}

export type GenerationOutcome = 'completed' | 'failed' | 'stopped' | 'skipped'

export function usePanelGeneration({
  projectRef,
  episodeId,
  dispatch,
  service = imageGenerationService,
  concurrency = 2,
  onGenerated,
}: Options) {
  const controllers = useRef(new Map<string, AbortController>())
  const [batchRunning, setBatchRunning] = useState(false)
  const batchCancelled = useRef(false)
  const concurrencyRef = useRef(concurrency)
  concurrencyRef.current = concurrency
  const resumedEpisodeRef = useRef<string | null>(null)

  useEffect(() => {
    const map = controllers.current
    return () => map.forEach((c) => c.abort())
  }, [])

  const runPanel = useCallback(
    async (
      panelId: string,
      controller: AbortController,
      submittedTaskId?: string,
      acknowledgeTrial = false,
    ): Promise<GenerationOutcome> => {
      const panel = projectRef.current.panels.find((p) => p.id === panelId)
      if (!panel) return 'skipped'
      const previous = { imageUrl: panel.imageUrl, hadImage: Boolean(panel.imageUrl) }

      const referenceImageUrls = projectRef.current.characters
        .filter((c) => panel.characterIds.includes(c.id))
        .map((c) => c.referenceImageUrl)

      try {
        const request = {
          panelId,
          prompt: panel.imagePrompt,
          aspectRatio: panel.aspectRatio,
          referenceImageUrls,
          signal: controller.signal,
          acknowledgeTrial,
          onProgress: (progress: number) =>
            dispatch({ type: 'panelRuntime', id: panelId, patch: { progress, status: 'generating' as const } }),
        }
        const result = submittedTaskId
          ? await service.complete(request, submittedTaskId)
          : await service.generate(request)
        dispatch({
          type: 'panelGenerated',
          id: panelId,
          patch: {
            status: 'completed',
            progress: 100,
            imageUrl: result.imageUrl,
            imageSource: result.source,
            generatedAt: result.generatedAt,
            errorMessage: null,
          },
        })
        onGenerated?.()
        return 'completed'
      } catch (error) {
        if (isAbortError(error)) {
          dispatch({
            type: 'panelRuntime',
            id: panelId,
            patch: { status: previous.hadImage ? 'completed' : 'draft', progress: previous.hadImage ? 100 : 0 },
          })
          return 'stopped'
        }
        const message = error instanceof Error ? error.message : '未知错误'
        dispatch({
          type: 'panelRuntime',
          id: panelId,
          patch: { status: 'failed', progress: 0, errorMessage: message },
        })
        return 'failed'
      } finally {
        controllers.current.delete(panelId)
      }
    },
    [dispatch, onGenerated, projectRef, service],
  )

  const generatePanel = useCallback(
    async (
      panelId: string,
      submittedTaskId?: string,
      acknowledgeTrial = false,
    ): Promise<GenerationOutcome> => {
      if (controllers.current.has(panelId)) return 'skipped'
      const panel = projectRef.current.panels.find((p) => p.id === panelId)
      if (!panel) return 'skipped'
      if (!acknowledgeTrial && projectRef.current.characters.length === 0 && !submittedTaskId) {
        toast.error('作品尚无角色', {
          description: '请先建立角色并建议锁定定妆；若要试画，请在分镜画布确认后继续。',
        })
        return 'skipped'
      }

      const controller = new AbortController()
      controllers.current.set(panelId, controller)
      dispatch({
        type: 'panelRuntime',
        id: panelId,
        patch: { status: 'generating', progress: 0, errorMessage: null },
      })
      try {
        return await runPanel(panelId, controller, submittedTaskId, acknowledgeTrial)
      } finally {
        controllers.current.delete(panelId)
      }
    },
    [dispatch, projectRef, runPanel],
  )

  const resumeActive = useCallback(async () => {
    if (resumedEpisodeRef.current === episodeId) return
    resumedEpisodeRef.current = episodeId
    try {
      const tasks = await listActiveEpisodePanelTasks(episodeId)
      const latestByPanel = new Map<string, string>()
      for (const task of tasks) {
        if (!task.panel_id) continue
        if (!latestByPanel.has(task.panel_id)) latestByPanel.set(task.panel_id, task.id)
      }
      await Promise.all(
        [...latestByPanel.entries()].map(async ([panelId, taskId]) => {
          if (controllers.current.has(panelId)) return
          const outcome = await generatePanel(panelId, taskId)
          const n = projectRef.current.panels.find((p) => p.id === panelId)?.panelNumber
          if (outcome === 'completed' && n != null) toast.success(`第 ${n} 格已完成`)
          if (outcome === 'failed' && n != null) {
            toast.error(`第 ${n} 格生成失败`, { description: '可在面板或底部状态栏重试' })
          }
        }),
      )
    } catch {
      resumedEpisodeRef.current = null
    }
  }, [episodeId, generatePanel, projectRef])

  useEffect(() => {
    void resumeActive()
  }, [resumeActive])

  const generateOne = useCallback(
    async (panelId: string, options?: { acknowledgeTrial?: boolean }) => {
      const panel = projectRef.current.panels.find((p) => p.id === panelId)
      if (!panel) return
      if (controllers.current.has(panelId)) {
        toast.info(`第 ${panel.panelNumber} 格正在生成，请勿重复提交`)
        return
      }
      const outcome = await generatePanel(panelId, undefined, options?.acknowledgeTrial ?? false)
      const n = projectRef.current.panels.find((p) => p.id === panelId)?.panelNumber ?? panel.panelNumber
      if (outcome === 'completed') toast.success(`第 ${n} 格已完成`)
      if (outcome === 'failed') toast.error(`第 ${n} 格生成失败`, { description: '可在面板或底部状态栏重试' })
      if (outcome === 'stopped') {
        toast(`已停止跟踪第 ${n} 格的生成进度`, {
          description: '服务端任务仍会继续，刷新后可恢复进度',
        })
      }
      return outcome
    },
    [generatePanel, projectRef],
  )

  const generateAll = useCallback(async (options?: { acknowledgeTrial?: boolean }) => {
    if (batchRunning) return
    const queue = projectRef.current.panels
      .filter((p) => !controllers.current.has(p.id))
      .map((p) => ({ id: p.id }))
    if (queue.length === 0) return

    setBatchRunning(true)
    batchCancelled.current = false
    const outcomes: GenerationOutcome[] = []
    const acknowledgeTrial = options?.acknowledgeTrial ?? false

    const worker = async () => {
      while (queue.length && !batchCancelled.current) {
        const next = queue.shift()!
        outcomes.push(await generatePanel(next.id, undefined, acknowledgeTrial))
      }
    }
    await Promise.all(Array.from({ length: concurrencyRef.current }, worker))
    setBatchRunning(false)

    const done = outcomes.filter((o) => o === 'completed').length
    const failed = outcomes.filter((o) => o === 'failed').length
    if (batchCancelled.current) {
      toast('已停止跟踪批量生成进度', {
        description: `本地已完成 ${done} 格；服务端未完成的任务仍会继续`,
      })
    } else if (failed) {
      toast.warning(`批量生成结束：${done} 格完成，${failed} 格失败`, { description: '失败的分镜可单独重试' })
    } else {
      toast.success(`全部 ${done} 格已完成`)
    }
  }, [batchRunning, generatePanel, projectRef])

  const cancelPanel = useCallback((panelId: string) => {
    controllers.current.get(panelId)?.abort()
  }, [])

  const cancelAll = useCallback(() => {
    batchCancelled.current = true
    controllers.current.forEach((c) => c.abort())
  }, [])

  const isPanelBusy = useCallback((panelId: string) => controllers.current.has(panelId), [])

  const busyPanelIds = useCallback(() => new Set(controllers.current.keys()), [])

  return {
    providerName: service.providerName,
    batchRunning,
    generateOne,
    generateAll,
    cancelPanel,
    cancelAll,
    isPanelBusy,
    busyPanelIds,
  }
}

export type PanelGeneration = ReturnType<typeof usePanelGeneration>
