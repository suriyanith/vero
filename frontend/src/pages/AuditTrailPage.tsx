import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { DecisionBadge } from '../components/badges'
import { Button, Card, MicroLabel, PageTitle, inputClass } from '../components/ui'

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
const filterInput = `${inputClass} rounded-full py-1`

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

  return (
    <div>
      <PageTitle title="Audit trail">
        <a
          href={`/api/decisions/export.csv?${params}`}
          className="ml-auto rounded-full border border-line-strong px-3.5 py-1.5 text-sm font-medium text-ink-soft transition-colors hover:bg-stone-100 hover:text-ink"
        >
          Export CSV
        </a>
      </PageTitle>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          Reviewer
          <input
            value={reviewer}
            onChange={(e) => {
              setReviewer(e.target.value)
              setOffset(0)
            }}
            placeholder="username"
            className={`w-32 ${filterInput}`}
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          Action
          <select
            value={action}
            onChange={(e) => {
              setAction(e.target.value)
              setOffset(0)
            }}
            className={`${filterInput}`}
          >
            <option value="">all</option>
            <option value="accept">accept</option>
            <option value="reject">reject</option>
            <option value="modify">modify</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          Code
          <input
            value={code}
            onChange={(e) => {
              setCode(e.target.value)
              setOffset(0)
            }}
            placeholder="E11.22"
            className={`w-28 font-mono ${filterInput}`}
          />
        </label>
      </div>

      {isPending && <p className="mt-8 text-ink-faint">Loading…</p>}
      {isError && <p className="mt-8 text-[#9a2c21]">Could not load the audit trail.</p>}
      {data && data.items.length === 0 && (
        <Card className="mt-8 p-10 text-center text-sm text-ink-soft">
          No decisions match these filters.
        </Card>
      )}

      {data && data.items.length > 0 && (
        <>
          <Card className="mt-5 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[44rem] border-collapse text-sm">
                <thead>
                  <tr className="text-left">
                    {['When', 'Reviewer', 'Action', 'Code', 'Reason', 'Run'].map((header) => (
                      <th key={header} className="px-4 py-3">
                        <MicroLabel>{header}</MicroLabel>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-t border-line transition-colors hover:bg-stone-50"
                    >
                      <td className="px-4 py-3 tabular-nums text-ink-faint">
                        {new Date(item.created_at).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="px-4 py-3">{item.reviewer_name}</td>
                      <td className="px-4 py-3">
                        <DecisionBadge action={item.action} />
                      </td>
                      <td className="px-4 py-3 font-mono text-[13px]">
                        {item.original_code}
                        {item.action === 'modify' && item.final_code && (
                          <span className="text-accent"> → {item.final_code}</span>
                        )}
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 text-ink-soft" title={item.reason}>
                        {item.reason || '—'}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/runs/${item.run_id}`}
                          className="text-accent hover:underline"
                          title={item.note_title}
                        >
                          {item.run_mode} · {item.kind}
                        </Link>
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
              {offset + 1}–{Math.min(offset + PAGE_SIZE, data.count)} of {data.count}
            </span>
            <Button
              size="sm"
              disabled={offset + PAGE_SIZE >= data.count}
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
