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
  /** Bundled asset returned by the demo implementation. Ignored by real providers. */
  demoAssetUrl?: string
  /** Demo-only switch used to exercise the failure + retry UI. */
  simulateFailure?: boolean
}

export interface ImageGenerationResult {
  imageUrl: string
  source: AssetSource
  providerName: string
  generatedAt: string
}

/**
 * A real implementation (e.g. Alibaba Tongyi Wanxiang) should POST to a
 * server route that holds the API key, submit an async task, and poll for
 * the result while reporting progress through `onProgress`.
 */
export interface ImageGenerationService {
  readonly isDemo: boolean
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
 * Simulates an async task with progress. It does NOT generate anything:
 * it returns the bundled example asset and labels it as a demo placeholder.
 */
export class DemoImageGenerationService implements ImageGenerationService {
  readonly isDemo = true
  readonly providerName = '前端演示（未连接图像模型）'

  generate({
    prompt,
    signal,
    onProgress,
    demoAssetUrl,
    simulateFailure,
  }: ImageGenerationRequest): Promise<ImageGenerationResult> {
    return new Promise((resolve, reject) => {
      if (signal.aborted) return reject(new DOMException('Aborted', 'AbortError'))
      if (!prompt.trim()) return reject(new ImageGenerationError('提示词为空，无法提交生成任务', false))

      const totalMs = 2200 + Math.random() * 1800
      const failAt = 0.55 + Math.random() * 0.2
      const start = performance.now()

      const interval = setInterval(() => {
        const ratio = Math.min(1, (performance.now() - start) / totalMs)
        onProgress?.(Math.round(ratio * 100))

        if (simulateFailure && ratio >= failAt) {
          clearInterval(interval)
          reject(new ImageGenerationError('演示：模拟的服务超时（504），请重试'))
          return
        }
        if (ratio >= 1) {
          clearInterval(interval)
          if (!demoAssetUrl) {
            reject(new ImageGenerationError('演示模式下此格没有可用的示例素材', false))
            return
          }
          resolve({
            imageUrl: demoAssetUrl,
            source: 'demo',
            providerName: this.providerName,
            generatedAt: new Date().toISOString(),
          })
        }
      }, 120)

      signal.addEventListener(
        'abort',
        () => {
          clearInterval(interval)
          reject(new DOMException('Aborted', 'AbortError'))
        },
        { once: true },
      )
    })
  }
}

export const imageGenerationService: ImageGenerationService = new DemoImageGenerationService()

/**
 * Submits an async Tongyi Wanxiang task through `/api/images` (which holds
 * DASHSCOPE_API_KEY) and polls `/api/images/:taskId`. DashScope does not
 * report real progress, so progress is estimated from elapsed time.
 */
export class WanxImageGenerationService implements ImageGenerationService {
  readonly isDemo = false
  readonly providerName: string

  constructor() {
    this.providerName = '服务端演示生成'
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
      source: 'demo',
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
  return new WanxImageGenerationService()
}
