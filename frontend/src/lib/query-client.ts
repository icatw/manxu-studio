import { QueryClient } from '@tanstack/react-query'

/** Shared client used by main.tsx and imperative wait helpers. */
export const queryClient = new QueryClient()
