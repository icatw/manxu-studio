import type { AssetSource } from '@/types/story'
import type { AspectRatio } from '@/types/storyboard'
import { api } from '@/lib/api/client'
import { waitForTask } from '@/services/workspace-api'

export interface ImageGenerationRequest {
  panelId: string
  prompt: string
  aspectRatio: AspectRatio
  referenceImageUrls: string[]
  signal: AbortSignal
  /** Folder used when the result is persisted to Blob storage. */
  kind?: 'panels' | 'characters' | 'scenes'
  onProgress?: (progress: number) => void
}

export interface ImageGenerationResult {
  imageUrl: string
  source: AssetSource
  providerName: string
  generatedAt: string
}

/**
 * The provider API key remains server-side; the browser only polls task state.
 */
export interface ImageGenerationService {
  readonly providerName: string
  generate(request: ImageGenerationRequest): Promise<ImageGenerationResult>
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

/**
 * Submits an async Qwen Image task and polls the persisted FastAPI task.
 */
export class QwenImageGenerationService implements ImageGenerationService {
  readonly providerName: string

  constructor() {
    this.providerName = 'Qwen Image'
  }

  async generate({ panelId, prompt, signal, onProgress }: ImageGenerationRequest): Promise<ImageGenerationResult> {
    if (!prompt.trim()) throw new ImageGenerationError('提示词为空，无法提交生成任务', false)
    const { data: submitted, error } = await api.POST('/panels/{panel_id}/image-generations', {
      params: { path: { panel_id: panelId } },
      body: { instruction: prompt },
      signal,
    })
    if (error || !submitted) throw new ImageGenerationError('无法提交图像任务，请检查 API 服务')
    const task = await waitForTask(submitted.id, onProgress, signal)
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

export function createImageGenerationService(settings: {
  provider: string
  model: string
  negativePrompt: string
}): ImageGenerationService {
  void settings
  return new QwenImageGenerationService()
}

export const imageGenerationService: ImageGenerationService = new QwenImageGenerationService()
