import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { PagedRuns, RunCreated, RunDetail, Sample } from '../../api/types'

const ACTIVE_STATUSES = new Set(['queued', 'processing'])

export function useSamples() {
  return useQuery({ queryKey: ['samples'], queryFn: () => api<Sample[]>('/samples') })
}

export function useRuns(params: {
  status?: string
  mode?: string
  mine?: boolean
  offset?: number
  limit?: number
}) {
  const search = new URLSearchParams()
  if (params.status) search.set('status', params.status)
  if (params.mode) search.set('mode', params.mode)
  if (params.mine) search.set('mine', 'true')
  search.set('limit', String(params.limit ?? 20))
  search.set('offset', String(params.offset ?? 0))
  return useQuery({
    queryKey: ['runs', Object.fromEntries(search)],
    queryFn: () => api<PagedRuns>(`/runs?${search}`),
    // Keep polling while anything is still moving through the queue.
    refetchInterval: (query) =>
      query.state.data?.items.some((run) => ACTIVE_STATUSES.has(run.status)) ? 2000 : false,
  })
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => api<RunDetail>(`/runs/${runId}`),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      query.state.data && ACTIVE_STATUSES.has(query.state.data.status) ? 2000 : false,
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      text?: string
      sample_id?: string
      mode?: string
      submitted_codes?: string[]
    }) => api<RunCreated>('/runs', { method: 'POST', json: payload }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
}

export function useCreateBatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData()
      form.set('mode', 'coding')
      for (const file of files) form.append('files', file)
      return api<{
        batch_id: string
        run_ids: string[]
        rejected: { filename: string; reason: string }[]
      }>('/batches', { method: 'POST', form })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
}

export function useRetryRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => api<RunCreated>(`/runs/${runId}/retry`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
}
