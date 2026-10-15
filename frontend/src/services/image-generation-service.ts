import type { AssetSource } from '@/types/story'
import type { AspectRatio } from '@/types/storyboard'
import { api } from '@/lib/api/client'
import { waitForGenerationTask } from '@/lib/generation-task'
import { queryClient } from '@/lib/query-client'

export interface ImageGenerationRequest {
  panelId: string
  prompt: string
  aspectRatio: AspectRatio
  referenceImageUrls: string[]
  signal: AbortSignal
  kind?: 'panels' | 'characters' | 'scenes'
  onProgress?: (progress: number) => void
  idempotencyKey?: string
}

export interface ImageGenerationResult {
  imageUrl: string
  source: AssetSource
  providerName: string
  generatedAt: string
}

/**
 * Browser only submits tasks and polls state; provider credentials stay on the server.
 */
export interface ImageGenerationService {
  readonly providerName: string
  generate(request: ImageGenerationRequest): Promise<ImageGenerationResult>
  /** Resume polling an already-submitted durable task. */
  complete(request: ImageGenerationRequest, taskId: string): Promise<ImageGenerationResult>
}

export class ImageGenerationError extends Error {
  constructor(
    message: string,
    readonly retryable = true,
  ) {
    super(message)
    this.name = 'ImageGenerationError'
  }
}

export function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === 'AbortError'
}

export class ServerImageGenerationService implements ImageGenerationService {
  readonly providerName = 'Server image provider'

  async generate({
    panelId,
    prompt,
    signal,
    onProgress,
    idempotencyKey,
  }: ImageGenerationRequest): Promise<ImageGenerationResult> {
    if (!prompt.trim()) throw new ImageGenerationError('提示词为空，无法提交生成任务', false)
    const { data: submitted, error } = await api.POST('/panels/{panel_id}/image-generations', {
      params: { path: { panel_id: panelId } },
      body: {
        instruction: prompt,
        ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}),
      },
      signal,
    })
    if (error || !submitted) throw new ImageGenerationError('无法提交图像任务，请检查 API 服务')
    return this.complete(
      { panelId, prompt, aspectRatio: '4:3', referenceImageUrls: [], signal, onProgress },
      submitted.id,
    )
  }

  async complete(
    { panelId, signal, onProgress }: ImageGenerationRequest,
    taskId: string,
  ): Promise<ImageGenerationResult> {
    const task = await waitForGenerationTask(queryClient, taskId, { onProgress, signal })
    const { data: versions, error: versionsError } = await api.GET('/panels/{panel_id}/image-versions', {
      params: { path: { panel_id: panelId } },
      signal,
    })
    if (versionsError || !versions?.length) throw new ImageGenerationError('任务完成，但没有找到图像版本')
    const resultAssetId =
      task.result && 'asset_id' in task.result ? task.result.asset_id : undefined
    const version = versions.find((item) => item.asset_id === resultAssetId) ?? versions[0]
    onProgress?.(100)
    return {
      imageUrl: version.image_url,
      source: 'ai',
      providerName: this.providerName,
      generatedAt: version.created_at,
    }
  }
}

export const imageGenerationService: ImageGenerationService = new ServerImageGenerationService()
