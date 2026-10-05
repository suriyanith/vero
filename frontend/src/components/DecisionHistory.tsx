import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DecisionBadge } from './badges'

interface HistoryItem {
  id: string
  created_at: string
  reviewer_name: string
  action: string
  original_code: string
  final_code: string
  reason: string
}

// Every decision ever made on this run (append-only), newest first,
// plus the per-run CSV export.
export function DecisionHistory({ runId }: { runId: string }) {
  const { data } = useQuery({
    queryKey: ['decisions', 'run', runId],
    queryFn: () =>
      api<{ items: HistoryItem[]; count: number }>(`/decisions?run=${runId}&limit=100`),
  })

  return (
    <section aria-label="Decision history" className="mt-6 border-t border-gray-200 pt-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Decision history</h2>
        <a
          href={`/api/runs/${runId}/export.csv`}
          className="rounded border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-100"
        >
          Export CSV
        </a>
      </div>
      {data && data.items.length === 0 && (
        <p className="mt-2 text-sm text-gray-500">No decisions yet.</p>
      )}
      <ul className="mt-2 space-y-1">
        {data?.items.map((item) => (
          <li key={item.id} className="flex items-baseline gap-2 text-sm">
            <span className="w-40 shrink-0 text-xs text-gray-500">
              {new Date(item.created_at).toLocaleString()}
            </span>
            <DecisionBadge action={item.action} />
            <span className="font-mono">
              {item.original_code}
              {item.action === 'modify' && item.final_code && <> → {item.final_code}</>}
            </span>
            <span className="text-gray-600">by {item.reviewer_name}</span>
            {item.reason && <span className="truncate text-gray-500">— “{item.reason}”</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}
