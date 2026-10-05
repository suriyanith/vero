import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { DecisionBadge } from '../components/badges'

interface TrailItem {
  id: string
  created_at: string
  reviewer_name: string
  action: string
  original_code: string
  final_code: string
  reason: string
  run_id: string
  run_mode: string
  note_title: string
  kind: string
}

const PAGE_SIZE = 25

export function AuditTrailPage() {
  const [reviewer, setReviewer] = useState('')
  const [action, setAction] = useState('')
  const [code, setCode] = useState('')
  const [offset, setOffset] = useState(0)

  const params = new URLSearchParams()
  if (reviewer) params.set('reviewer', reviewer)
  if (action) params.set('action', action)
  if (code) params.set('code', code)
  params.set('limit', String(PAGE_SIZE))
  params.set('offset', String(offset))

  const { data, isPending, isError } = useQuery({
    queryKey: ['decisions', params.toString()],
    queryFn: () => api<{ items: TrailItem[]; count: number }>(`/decisions?${params}`),
  })

  const exportUrl = `/api/decisions/export.csv?${params}`

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-bold">Audit trail</h1>
        <label className="text-sm text-gray-600">
          Reviewer{' '}
          <input
            value={reviewer}
            onChange={(e) => {
              setReviewer(e.target.value)
              setOffset(0)
            }}
            placeholder="username"
            className="w-28 rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-sm text-gray-600">
          Action{' '}
          <select
            value={action}
            onChange={(e) => {
              setAction(e.target.value)
              setOffset(0)
            }}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">all</option>
            <option value="accept">accept</option>
            <option value="reject">reject</option>
            <option value="modify">modify</option>
          </select>
        </label>
        <label className="text-sm text-gray-600">
          Code{' '}
          <input
            value={code}
            onChange={(e) => {
              setCode(e.target.value)
              setOffset(0)
            }}
            placeholder="E11.22"
            className="w-24 rounded border border-gray-300 px-2 py-1 font-mono text-sm"
          />
        </label>
        <a
          href={exportUrl}
          className="ml-auto rounded border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-100"
        >
          Export CSV
        </a>
      </div>

      {isPending && <p className="mt-6 text-gray-500">Loading…</p>}
      {isError && <p className="mt-6 text-red-700">Could not load the audit trail.</p>}
      {data && data.items.length === 0 && (
        <p className="mt-6 text-gray-500">No decisions match these filters.</p>
      )}

      {data && data.items.length > 0 && (
        <>
          <table className="mt-4 w-full border-collapse overflow-hidden rounded-lg bg-white text-sm shadow-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-3 py-2">When</th>
                <th className="px-3 py-2">Reviewer</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Reason</th>
                <th className="px-3 py-2">Run</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100 hover:bg-blue-50">
                  <td className="px-3 py-2 text-gray-500">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">{item.reviewer_name}</td>
                  <td className="px-3 py-2">
                    <DecisionBadge action={item.action} />
                  </td>
                  <td className="px-3 py-2 font-mono">
                    {item.original_code}
                    {item.action === 'modify' && item.final_code && (
                      <span className="text-blue-700"> → {item.final_code}</span>
                    )}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-gray-600" title={item.reason}>
                    {item.reason || '—'}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      to={`/runs/${item.run_id}`}
                      className="text-blue-700 hover:underline"
                      title={item.note_title}
                    >
                      {item.run_mode} · {item.kind}
                    </Link>
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
              {offset + 1}–{Math.min(offset + PAGE_SIZE, data.count)} of {data.count}
            </span>
            <button
              className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
              disabled={offset + PAGE_SIZE >= data.count}
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
