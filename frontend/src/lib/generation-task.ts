import type { QueryClient } from '@tanstack/react-query'
import { ApiError, api, toApiError } from '@/lib/api/client'
import type { components } from '@/lib/api/schema'

export type GenerationTaskDto = components['schemas']['GenerationTask']

export function generationTaskQueryKey(taskId: string) {
  return ['generation-task', taskId] as const
}

export function isTerminalGenerationStatus(status: GenerationTaskDto['status']) {
  return status === 'succeeded' || status === 'failed'
}

export async function fetchGenerationTask(taskId: string, signal?: AbortSignal): Promise<GenerationTaskDto> {
  const { data, error } = await api.GET('/generation-tasks/{task_id}', {
    params: { path: { task_id: taskId } },
    signal,
  })
  if (error || data === undefined) throw toApiError(error, '无法读取生成任务状态')
  return data
}

function delay(milliseconds: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const timeout = window.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, milliseconds)
    const onAbort = () => {
      window.clearTimeout(timeout)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

function taskFailureMessage(task: GenerationTaskDto) {
  const error = task.error
  if (!error || typeof error !== 'object') return '任务失败，请重试'
  if ('detail' in error && typeof error.detail === 'string') return error.detail
  if ('message' in error && typeof error.message === 'string') return error.message
  if ('title' in error && typeof error.title === 'string') return error.title
  return '任务失败，请重试'
}

function isRateLimited(error: unknown) {
  return error instanceof ApiError && error.code === 'RATE_LIMITED'
}

/** Poll via TanStack Query cache until terminal or aborted. */
export async function waitForGenerationTask(
  queryClient: QueryClient,
  taskId: string,
  options?: { onProgress?: (progress: number) => void; signal?: AbortSignal },
): Promise<GenerationTaskDto> {
  let pollDelayMs = 2000
  while (!options?.signal?.aborted) {
    try {
      const task = await queryClient.fetchQuery({
        queryKey: generationTaskQueryKey(taskId),
        queryFn: () => fetchGenerationTask(taskId, options?.signal),
        staleTime: 0,
      })
      options?.onProgress?.(task.progress ?? 0)
      if (task.status === 'succeeded') return task
      if (task.status === 'failed') throw new Error(taskFailureMessage(task))
    } catch (error) {
      if (isRateLimited(error)) {
        await delay(Math.max(pollDelayMs, 5000), options?.signal)
        pollDelayMs = Math.min(pollDelayMs + 1000, 15000)
        continue
      }
      throw error
    }
    await delay(pollDelayMs, options?.signal)
    pollDelayMs = Math.min(pollDelayMs + 1000, 15000)
  }
  throw new DOMException('Aborted', 'AbortError')
}

export function stopTrackingGenerationTask(queryClient: QueryClient, taskId: string) {
  void queryClient.cancelQueries({ queryKey: generationTaskQueryKey(taskId) })
}
