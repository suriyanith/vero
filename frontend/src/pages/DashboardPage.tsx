import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import { useRuns } from '../features/runs/hooks'
import { StatusBadge } from '../components/badges'

// One steady hue for single-series marks; identity never relies on color.
const MARK_COLOR = '#2563eb'
const GRID_COLOR = '#e5e7eb'
const INK_MUTED = '#6b7280'

interface Summary {
  days: number
  notes_processed: number
  failed_runs: Record<string, number>
  average_processing_ms: number | null
  suggestions_made: number
  acceptance_rate: number | null
  override_rate: number | null
  acceptance_rate_by_confidence: Record<string, number | null>
  hccs_captured: number
  unsupported_codes_caught: number
  missed_hccs_found: number
  review_backlog: number
  ai_usage: {
    calls: number
    input_tokens: number
    output_tokens: number
    cache_hit_rate: number | null
  }
  runs_per_day: { day: string; count: number }[]
}

const percent = (value: number | null | undefined) =>
  value == null ? '—' : `${Math.round(value * 100)}%`

function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  )
}

export function DashboardPage() {
  const [days, setDays] = useState(30)
  const { data, isPending, isError } = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => api<Summary>(`/dashboard/summary?days=${days}`),
  })
  const backlog = useRuns({ status: 'ready_for_review', limit: 5 })

  if (isPending) return <p className="text-gray-500">Loading…</p>
  if (isError || !data) return <p className="text-red-700">Could not load the dashboard.</p>

  const failures = Object.entries(data.failed_runs)
  const confidenceRates = ['high', 'medium', 'low'].map((level) => ({
    level,
    rate: data.acceptance_rate_by_confidence[level],
    percent:
      data.acceptance_rate_by_confidence[level] != null
        ? Math.round((data.acceptance_rate_by_confidence[level] as number) * 100)
        : null,
  }))

  return (
    <div>
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold">Dashboard</h1>
        <label className="text-sm text-gray-600">
          Window{' '}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </label>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="Notes processed" value={String(data.notes_processed)} />
        <MetricCard
          label="Failed runs"
          value={String(failures.reduce((n, [, c]) => n + c, 0))}
          hint={failures.map(([code, c]) => `${code}: ${c}`).join(', ') || undefined}
        />
        <MetricCard
          label="Avg processing"
          value={
            data.average_processing_ms != null
              ? `${(data.average_processing_ms / 1000).toFixed(1)}s`
              : '—'
          }
        />
        <MetricCard label="Suggestions" value={String(data.suggestions_made)} />
        <MetricCard label="Acceptance rate" value={percent(data.acceptance_rate)} />
        <MetricCard label="Override rate" value={percent(data.override_rate)} />
        <MetricCard label="HCCs captured" value={String(data.hccs_captured)} />
        <MetricCard
          label="Unsupported caught"
          value={String(data.unsupported_codes_caught)}
          hint={`missed HCCs found: ${data.missed_hccs_found}`}
        />
        <MetricCard label="Review backlog" value={String(data.review_backlog)} />
        <MetricCard
          label="AI calls"
          value={String(data.ai_usage.calls)}
          hint={`cache hits ${percent(data.ai_usage.cache_hit_rate)}`}
        />
        <MetricCard
          label="Tokens in / out"
          value={`${data.ai_usage.input_tokens} / ${data.ai_usage.output_tokens}`}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-gray-800">Runs per day</h2>
          <div className="mt-2 h-56">
            <ResponsiveContainer>
              <LineChart
                data={data.runs_per_day}
                margin={{ top: 8, right: 8, bottom: 0, left: -24 }}
              >
                <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 11, fill: INK_MUTED }}
                  tickLine={false}
                  axisLine={{ stroke: GRID_COLOR }}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: INK_MUTED }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={MARK_COLOR}
                  strokeWidth={2}
                  dot={{ r: 3, fill: MARK_COLOR }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-gray-800">
            Acceptance rate by confidence
            <span className="ml-2 font-normal text-gray-500">
              (High should beat Low, or the rules need work)
            </span>
          </h2>
          <div className="mt-2 h-56">
            <ResponsiveContainer>
              <BarChart data={confidenceRates} margin={{ top: 16, right: 8, bottom: 0, left: -24 }}>
                <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="level"
                  tick={{ fontSize: 12, fill: INK_MUTED }}
                  tickLine={false}
                  axisLine={{ stroke: GRID_COLOR }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: INK_MUTED }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip formatter={(value) => [`${value}%`, 'accepted']} />
                <Bar dataKey="percent" fill={MARK_COLOR} radius={[4, 4, 0, 0]} maxBarSize={48}>
                  <LabelList
                    dataKey="percent"
                    position="top"
                    formatter={(value) => (value == null ? 'n/a' : `${String(value)}%`)}
                    style={{ fontSize: 12, fill: '#1f2937' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="mt-6">
        <h2 className="text-sm font-semibold text-gray-800">Waiting for review</h2>
        {backlog.data?.items.length === 0 && (
          <p className="mt-1 text-sm text-gray-500">Nothing waiting. </p>
        )}
        <ul className="mt-2 space-y-1">
          {backlog.data?.items.map((run) => (
            <li key={run.id} className="rounded border border-gray-200 bg-white p-2 text-sm">
              <Link to={`/runs/${run.id}`} className="font-medium text-blue-700 hover:underline">
                {run.note_title}
              </Link>
              <span className="ml-2">
                <StatusBadge status={run.status} />
              </span>
              <span className="ml-2 text-gray-500">{run.suggestion_count} suggestion(s)</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
