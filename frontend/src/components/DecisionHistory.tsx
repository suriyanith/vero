import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DecisionBadge } from './badges'
import { MicroLabel } from './ui'

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
    <section aria-label="Decision history" className="mt-10">
      <div className="flex items-center justify-between">
        <MicroLabel>Decision history</MicroLabel>
        <a
          href={`/api/runs/${runId}/export.csv`}
          className="rounded-full border border-line-strong px-3 py-1 text-[13px] font-medium text-ink-soft transition-colors hover:bg-stone-100 hover:text-ink"
        >
          Export CSV
        </a>
      </div>
      {data && data.items.length === 0 && (
        <p className="mt-2.5 text-sm text-ink-faint">No decisions yet.</p>
      )}
      <ul className="mt-2.5 space-y-1.5">
        {data?.items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1 text-sm">
            <span className="w-full text-xs tabular-nums text-ink-faint sm:w-36 sm:shrink-0">
              {new Date(item.created_at).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
              })}
            </span>
            <DecisionBadge action={item.action} />
            <span className="font-mono text-[13px] font-medium">
              {item.original_code}
              {item.action === 'modify' && item.final_code && <> → {item.final_code}</>}
            </span>
            <span className="text-ink-soft">by {item.reviewer_name}</span>
            {item.reason && <span className="truncate text-ink-faint">— “{item.reason}”</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}
