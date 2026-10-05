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
import { StatusBadge } from '../components/badges'
import { Card, MicroLabel, PageTitle } from '../components/ui'
import { useRuns } from '../features/runs/hooks'

// One steady hue for single-series marks; identity never relies on color.
const MARK_COLOR = '#5247c7'
const GRID_COLOR = '#e8e4da'
const INK_MUTED = '#a8a29e'

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
    <Card className="p-4">
      <MicroLabel>{label}</MicroLabel>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight tabular-nums">{value}</p>
      {hint && (
        <p className="mt-0.5 truncate text-xs text-ink-faint" title={hint}>
          {hint}
        </p>
      )}
    </Card>
  )
}

export function DashboardPage() {
  const [days, setDays] = useState(30)
  const { data, isPending, isError } = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => api<Summary>(`/dashboard/summary?days=${days}`),
  })
  const backlog = useRuns({ status: 'ready_for_review', limit: 5 })

  if (isPending) return <p className="text-ink-faint">Loading…</p>
  if (isError || !data) return <p className="text-[#9a2c21]">Could not load the dashboard.</p>

  const failures = Object.entries(data.failed_runs)
  const confidenceRates = ['high', 'medium', 'low'].map((level) => ({
    level,
    percent:
      data.acceptance_rate_by_confidence[level] != null
        ? Math.round((data.acceptance_rate_by_confidence[level] as number) * 100)
        : null,
  }))

  return (
    <div>
      <PageTitle title="Dashboard">
        <div className="ml-auto inline-flex gap-0.5 rounded-full border border-line bg-stone-100 p-1">
          {[7, 30, 90].map((window) => (
            <button
              key={window}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                days === window ? 'bg-surface text-ink shadow-sm' : 'text-ink-soft hover:text-ink'
              }`}
              onClick={() => setDays(window)}
            >
              {window}d
            </button>
          ))}
        </div>
      </PageTitle>

      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
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

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <MicroLabel>Runs per day</MicroLabel>
          <div className="mt-3 h-56">
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
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: '1px solid #e8e4da',
                    background: '#fffefb',
                    fontSize: 13,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={MARK_COLOR}
                  strokeWidth={2}
                  dot={{ r: 3, fill: MARK_COLOR, strokeWidth: 0 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5">
          <MicroLabel>Acceptance rate by confidence</MicroLabel>
          <p className="mt-1 text-xs text-ink-faint">
            High should beat Low, or the rules need work.
          </p>
          <div className="mt-2 h-[12.5rem]">
            <ResponsiveContainer>
              <BarChart data={confidenceRates} margin={{ top: 18, right: 8, bottom: 0, left: -24 }}>
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
                <Tooltip
                  formatter={(value) => [`${value}%`, 'accepted']}
                  contentStyle={{
                    borderRadius: 12,
                    border: '1px solid #e8e4da',
                    background: '#fffefb',
                    fontSize: 13,
                  }}
                />
                <Bar dataKey="percent" fill={MARK_COLOR} radius={[4, 4, 0, 0]} maxBarSize={44}>
                  <LabelList
                    dataKey="percent"
                    position="top"
                    formatter={(value) => (value == null ? 'n/a' : `${String(value)}%`)}
                    style={{ fontSize: 12, fill: '#1c1917' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <section className="mt-8">
        <MicroLabel>Waiting for review</MicroLabel>
        {backlog.data?.items.length === 0 && (
          <p className="mt-2 text-sm text-ink-faint">Nothing waiting.</p>
        )}
        <ul className="mt-2.5 space-y-2">
          {backlog.data?.items.map((run) => (
            <li key={run.id}>
              <Link
                to={`/runs/${run.id}`}
                className="flex items-center gap-3 rounded-xl border border-line bg-surface px-4 py-2.5 text-sm transition-colors hover:border-line-strong hover:bg-stone-50"
              >
                <span className="font-medium">{run.note_title}</span>
                <StatusBadge status={run.status} />
                <span className="ml-auto text-ink-faint">{run.suggestion_count} suggestion(s)</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
