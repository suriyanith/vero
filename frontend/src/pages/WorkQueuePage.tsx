import { useState } from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/badges'
import { Button, Card, MicroLabel, PageTitle } from '../components/ui'
import { useRetryRun, useRuns } from '../features/runs/hooks'

const PAGE_SIZE = 20
const STATUSES = ['', 'queued', 'processing', 'ready_for_review', 'completed', 'failed']

const selectClass =
  'rounded-full border border-line-strong bg-surface px-3 py-1 text-sm text-ink focus:border-accent focus:outline-none'

export function WorkQueuePage() {
  const [status, setStatus] = useState('')
  const [mine, setMine] = useState(false)
  const [offset, setOffset] = useState(0)
  const runs = useRuns({ status: status || undefined, mine, offset, limit: PAGE_SIZE })
  const retry = useRetryRun()

  return (
    <div>
      <PageTitle title="Work queue">
        <div className="ml-auto flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            Status
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value)
                setOffset(0)
              }}
              className={selectClass}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s === '' ? 'all' : s.replaceAll('_', ' ')}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-sm text-ink-soft">
            <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
            Only mine
          </label>
        </div>
      </PageTitle>

      {runs.isPending && <p className="mt-8 text-ink-faint">Loading…</p>}
      {runs.isError && <p className="mt-8 text-[#9a2c21]">Could not load the queue.</p>}
      {runs.data && runs.data.items.length === 0 && (
        <Card className="mt-8 p-10 text-center">
          <p className="font-display text-lg">Nothing in the queue</p>
          <p className="mt-1 text-sm text-ink-soft">
            <Link to="/new" className="font-medium text-accent hover:underline">
              Submit a note
            </Link>{' '}
            to get started.
          </p>
        </Card>
      )}

      {runs.data && runs.data.items.length > 0 && (
        <>
          <Card className="mt-6 overflow-hidden">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left">
                  {['Note', 'Status', 'Mode', 'Codes', 'Submitted by', 'Created', ''].map(
                    (header) => (
                      <th key={header} className="px-4 py-3">
                        <MicroLabel>{header}</MicroLabel>
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {runs.data.items.map((run) => (
                  <tr
                    key={run.id}
                    className="border-t border-line transition-colors hover:bg-stone-50"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/runs/${run.id}`}
                        className="font-medium text-ink hover:text-accent"
                      >
                        {run.note_title}
                      </Link>
                      {run.error_code && (
                        <span className="ml-2 text-xs text-[#9a2c21]">{run.error_code}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-3 text-ink-soft">{run.mode}</td>
                    <td className="px-4 py-3 tabular-nums text-ink-soft">{run.suggestion_count}</td>
                    <td className="px-4 py-3 text-ink-soft">{run.created_by_name}</td>
                    <td className="px-4 py-3 text-ink-faint">
                      {new Date(run.created_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {run.status === 'failed' && (
                        <Button size="sm" onClick={() => retry.mutate(run.id)}>
                          Retry
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div className="mt-4 flex items-center gap-3 text-sm">
            <Button
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </Button>
            <span className="tabular-nums text-ink-faint">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, runs.data.count)} of {runs.data.count}
            </span>
            <Button
              size="sm"
              disabled={offset + PAGE_SIZE >= runs.data.count}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
