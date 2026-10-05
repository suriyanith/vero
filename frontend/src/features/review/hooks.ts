import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { AcceptHighResult, Decision, DecisionInput, RunDetail } from '../../api/types'

// Decisions update the run-detail cache optimistically and roll back on error.
export function useDecide(runId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ suggestionId, input }: { suggestionId: number; input: DecisionInput }) =>
      api<Decision>(`/suggestions/${suggestionId}/decisions`, { method: 'POST', json: input }),
    onMutate: async ({ suggestionId, input }) => {
      await queryClient.cancelQueries({ queryKey: ['run', runId] })
      const previous = queryClient.getQueryData<RunDetail>(['run', runId])
      if (previous) {
        queryClient.setQueryData<RunDetail>(['run', runId], {
          ...previous,
          suggestions: previous.suggestions.map((s) =>
            s.id === suggestionId
              ? {
                  ...s,
                  latest_decision: {
                    action: input.action,
                    final_code:
                      input.final_code ?? (input.action === 'accept' ? s.display_code : ''),
                    reason: input.reason ?? '',
                    reviewer_name: 'you',
                    created_at: new Date().toISOString(),
                  },
                }
              : s,
          ),
        })
      }
      return { previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(['run', runId], context.previous)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['run', runId] }),
  })
}

export function useAcceptAllHigh(runId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<AcceptHighResult>(`/runs/${runId}/accept-high`, { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['run', runId] }),
  })
}
