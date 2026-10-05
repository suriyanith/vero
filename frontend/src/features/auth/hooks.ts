import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { User } from '../../api/types'

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api<User>('/auth/me', { allowUnauthorized: true }),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (credentials: { username: string; password: string }) =>
      // 401 here means wrong credentials, not an expired session: no redirect.
      api<User>('/auth/login', { method: 'POST', json: credentials, allowUnauthorized: true }),
    onSuccess: (user) => queryClient.setQueryData(['me'], user),
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
    onSuccess: () => queryClient.clear(),
  })
}
