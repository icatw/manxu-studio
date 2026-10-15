import { useQuery } from '@tanstack/react-query'
import {
  fetchGenerationTask,
  generationTaskQueryKey,
  isTerminalGenerationStatus,
} from '@/lib/generation-task'

/** Subscribe to a durable generation task; stops refetching at terminal status. */
export function useGenerationTask(taskId: string | null | undefined) {
  return useQuery({
    queryKey: generationTaskQueryKey(taskId ?? 'none'),
    queryFn: () => fetchGenerationTask(taskId!),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || isTerminalGenerationStatus(status)) return false
      const updates = query.state.dataUpdateCount
      return Math.min(2000 + updates * 1000, 15000)
    },
  })
}
