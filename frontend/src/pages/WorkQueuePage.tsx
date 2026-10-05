import { useState } from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/badges'
import { useRetryRun, useRuns } from '../features/runs/hooks'

const PAGE_SIZE = 20
const STATUSES = ['', 'queued', 'processing', 'ready_for_review', 'completed', 'failed']

export function WorkQueuePage() {
  const [status, setStatus] = useState('')
  const [mine, setMine] = useState(false)
  const [offset, setOffset] = useState(0)
  const runs = useRuns({ status: status || undefined, mine, offset, limit: PAGE_SIZE })
  const retry = useRetryRun()

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-bold">Work queue</h1>
        <label className="text-sm text-gray-600">
          Status{' '}
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setOffset(0)
            }}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === '' ? 'all' : s.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1 text-sm text-gray-600">
          <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
          Only mine
        </label>
      </div>

      {runs.isPending && <p className="mt-6 text-gray-500">Loading…</p>}
      {runs.isError && <p className="mt-6 text-red-700">Could not load the queue.</p>}
      {runs.data && runs.data.items.length === 0 && (
        <p className="mt-6 text-gray-500">
          No runs yet.{' '}
          <Link to="/new" className="text-blue-700 underline">
            Submit a note
          </Link>{' '}
          to get started.
        </p>
      )}

      {runs.data && runs.data.items.length > 0 && (
        <>
          <table className="mt-4 w-full border-collapse overflow-hidden rounded-lg bg-white text-sm shadow-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-3 py-2">Note</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Mode</th>
                <th className="px-3 py-2">Suggestions</th>
                <th className="px-3 py-2">Submitted by</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {runs.data.items.map((run) => (
                <tr key={run.id} className="border-b border-gray-100 hover:bg-blue-50">
                  <td className="px-3 py-2">
                    <Link
                      to={`/runs/${run.id}`}
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {run.note_title}
                    </Link>
                    {run.error_code && (
                      <span className="ml-2 text-xs text-red-700">{run.error_code}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-3 py-2">{run.mode}</td>
                  <td className="px-3 py-2">{run.suggestion_count}</td>
                  <td className="px-3 py-2">{run.created_by_name}</td>
                  <td className="px-3 py-2 text-gray-500">
                    {new Date(run.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    {run.status === 'failed' && (
                      <button
                        className="text-xs text-blue-700 underline"
                        onClick={() => retry.mutate(run.id)}
                      >
                        Retry
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 flex items-center gap-3 text-sm">
            <button
              className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </button>
            <span className="text-gray-500">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, runs.data.count)} of {runs.data.count}
            </span>
            <button
              className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
              disabled={offset + PAGE_SIZE >= runs.data.count}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}
