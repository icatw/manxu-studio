import { useQuery } from '@tanstack/react-query'
import { api, toApiError } from '@/lib/api/client'
import type { components } from '@/lib/api/schema'

export type AccountDto = components['schemas']['Account']

export const currentAccountQueryKey = ['current-account'] as const

export function useCurrentAccount() {
  return useQuery({
    queryKey: currentAccountQueryKey,
    queryFn: async (): Promise<AccountDto> => {
      const { data, error } = await api.GET('/auth/me')
      if (error || !data) throw toApiError(error, '无法读取当前账户')
      return data
    },
    retry: false,
  })
}
