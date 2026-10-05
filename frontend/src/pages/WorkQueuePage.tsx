import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { StatusBadge } from '../components/badges'
import { Button, Card, Checkbox, MicroLabel, PageTitle, Select } from '../components/ui'
import { useRetryRun, useRuns } from '../features/runs/hooks'

const PAGE_SIZE = 20
const STATUSES = ['', 'queued', 'processing', 'ready_for_review', 'completed', 'failed']

export function WorkQueuePage() {
  const [status, setStatus] = useState('')
  const [mine, setMine] = useState(false)
  const [offset, setOffset] = useState(0)
  const runs = useRuns({ status: status || undefined, mine, offset, limit: PAGE_SIZE })
  const retry = useRetryRun()
  const navigate = useNavigate()

  return (
    <div>
      <PageTitle title="Work queue">
        <div className="ml-auto flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            Status
            <Select
              pill
              value={status}
              onChange={(e) => {
                setStatus(e.target.value)
                setOffset(0)
              }}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s === '' ? 'all' : s.replaceAll('_', ' ')}
                </option>
              ))}
            </Select>
          </label>
          <Checkbox label="Only mine" checked={mine} onChange={setMine} />
        </div>
      </PageTitle>

      {runs.isPending && <p className="mt-8 text-ink-faint">Loading…</p>}
      {runs.isError && <p className="mt-8 text-[#9a2c21]">Could not load the queue.</p>}
      {runs.data && runs.data.items.length === 0 && (
        <div className="relative mt-8 overflow-hidden rounded-3xl border border-line bg-surface p-12 text-center sm:p-16">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                'radial-gradient(30rem 16rem at 50% -8rem, #e2ddf8 0%, rgba(226,221,248,0) 65%)',
            }}
          />
          <div className="relative">
            <p className="font-display text-2xl font-semibold tracking-tight">
              Nothing in the queue
            </p>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-ink-soft">
              Submit a synthetic note and Vero will suggest codes with the evidence to back them.
            </p>
            <Link
              to="/new"
              className="mt-5 inline-block rounded-full bg-ink px-5 py-2 text-sm font-medium text-paper shadow-sm transition-colors hover:bg-stone-700"
            >
              Submit a note
            </Link>
          </div>
        </div>
      )}

      {runs.data && runs.data.items.length > 0 && (
        <>
          <Card className="mt-6 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[40rem] border-collapse text-sm">
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
                      className="group cursor-pointer border-t border-line transition-colors hover:bg-stone-50"
                      onClick={() => navigate(`/runs/${run.id}`)}
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
                      <td className="px-4 py-3 tabular-nums text-ink-soft">
                        {run.suggestion_count}
                      </td>
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
            </div>
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
