'use client'

import { useCallback, useEffect, useRef, useState, type Dispatch, type RefObject } from 'react'
import { toast } from 'sonner'
import type { ProjectAction } from '@/lib/project-store'
import { imageGenerationService, isAbortError, type ImageGenerationService } from '@/services/image-generation-service'
import type { ComicProject } from '@/types/storyboard'

interface Options {
  projectRef: RefObject<ComicProject>
  dispatch: Dispatch<ProjectAction>
  service?: ImageGenerationService
  concurrency?: number
  onGenerated?: () => void
}

export type GenerationOutcome = 'completed' | 'failed' | 'cancelled' | 'skipped'

export function usePanelGeneration({
  projectRef,
  dispatch,
  service = imageGenerationService,
  concurrency = 2,
  onGenerated,
}: Options) {
  const controllers = useRef(new Map<string, AbortController>())
  const doneSuffix = ''
  const [batchRunning, setBatchRunning] = useState(false)
  const batchCancelled = useRef(false)
  const concurrencyRef = useRef(concurrency)
  concurrencyRef.current = concurrency

  useEffect(() => {
    const map = controllers.current
    return () => map.forEach((c) => c.abort())
  }, [])

  const generatePanel = useCallback(
    async (panelId: string): Promise<GenerationOutcome> => {
      if (controllers.current.has(panelId)) return 'skipped'
      const panel = projectRef.current.panels.find((p) => p.id === panelId)
      if (!panel) return 'skipped'

      const controller = new AbortController()
      controllers.current.set(panelId, controller)
      const previous = { imageUrl: panel.imageUrl, hadImage: Boolean(panel.imageUrl) }

      dispatch({
        type: 'panelRuntime',
        id: panelId,
        patch: { status: 'generating', progress: 0, errorMessage: null },
      })

      const referenceImageUrls = projectRef.current.characters
        .filter((c) => panel.characterIds.includes(c.id))
        .map((c) => c.referenceImageUrl)

      try {
        const result = await service.generate({
          panelId,
          prompt: panel.imagePrompt,
          aspectRatio: panel.aspectRatio,
          referenceImageUrls,
          signal: controller.signal,
          onProgress: (progress) =>
            dispatch({ type: 'panelRuntime', id: panelId, patch: { progress } }),
        })
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
          return 'cancelled'
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

  const generateOne = useCallback(
    async (panelId: string) => {
      const panel = projectRef.current.panels.find((p) => p.id === panelId)
      if (!panel) return
      if (controllers.current.has(panelId)) {
        toast.info(`第 ${panel.panelNumber} 格正在生成，请勿重复提交`)
        return
      }
      const outcome = await generatePanel(panelId)
      const n = projectRef.current.panels.find((p) => p.id === panelId)?.panelNumber ?? panel.panelNumber
      if (outcome === 'completed') toast.success(`第 ${n} 格已完成${doneSuffix}`)
      if (outcome === 'failed') toast.error(`第 ${n} 格生成失败`, { description: '可在面板或底部状态栏重试' })
      if (outcome === 'cancelled') toast(`已取消第 ${n} 格的生成任务`)
    },
    [generatePanel, projectRef, doneSuffix],
  )

  const generateAll = useCallback(async () => {
    if (batchRunning) return
    const queue = projectRef.current.panels
      .filter((p) => !controllers.current.has(p.id))
      .map((p) => ({ id: p.id }))
    if (queue.length === 0) return

    setBatchRunning(true)
    batchCancelled.current = false
    const outcomes: GenerationOutcome[] = []

    const worker = async () => {
      while (queue.length && !batchCancelled.current) {
        const next = queue.shift()!
        outcomes.push(await generatePanel(next.id))
      }
    }
    await Promise.all(Array.from({ length: concurrencyRef.current }, worker))
    setBatchRunning(false)

    const done = outcomes.filter((o) => o === 'completed').length
    const failed = outcomes.filter((o) => o === 'failed').length
    if (batchCancelled.current) toast('批量生成已取消', { description: `已完成 ${done} 格` })
    else if (failed) toast.warning(`批量生成结束：${done} 格完成，${failed} 格失败`, { description: '失败的分镜可单独重试' })
    else toast.success(`全部 ${done} 格已完成${doneSuffix}`)
  }, [batchRunning, generatePanel, projectRef, doneSuffix])

  const cancelPanel = useCallback((panelId: string) => {
    controllers.current.get(panelId)?.abort()
  }, [])

  const cancelAll = useCallback(() => {
    batchCancelled.current = true
    controllers.current.forEach((c) => c.abort())
  }, [])

  const isPanelBusy = useCallback((panelId: string) => controllers.current.has(panelId), [])

  return {
    providerName: service.providerName,
    batchRunning,
    generateOne,
    generateAll,
    cancelPanel,
    cancelAll,
    isPanelBusy,
  }
}

export type PanelGeneration = ReturnType<typeof usePanelGeneration>
