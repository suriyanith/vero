import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import { StatusBadge } from '../components/badges'
import { Card, MicroLabel, PageTitle, Segmented } from '../components/ui'
import { useRuns } from '../features/runs/hooks'

// One steady hue for single-series marks; identity never relies on color.
const MARK_COLOR = '#5247c7'
const GRID_COLOR = '#e8e4da'
const INK_MUTED = '#a8a29e'
const TOOLTIP_STYLE = {
  borderRadius: 12,
  border: '1px solid #e8e4da',
  background: '#fffefb',
  fontSize: 13,
}

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

function HeroStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <MicroLabel className="text-ink-soft/70">{label}</MicroLabel>
      <p className="mt-1 font-display text-3xl font-semibold tracking-tight tabular-nums sm:text-4xl xl:text-5xl">
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink-soft">{hint}</p>}
    </div>
  )
}

function MetricCard({
  label,
  value,
  hint,
  delay = 0,
}: {
  label: string
  value: string
  hint?: string
  delay?: number
}) {
  return (
    <div className="anim-in" style={{ animationDelay: `${delay}ms` }}>
      <Card interactive className="h-full min-w-0 p-4">
        <MicroLabel>{label}</MicroLabel>
        <p className="mt-1.5 truncate text-xl font-semibold tracking-tight tabular-nums sm:text-2xl">
          {value}
        </p>
        {hint && (
          <p className="mt-0.5 truncate text-xs text-ink-faint" title={hint}>
            {hint}
          </p>
        )}
      </Card>
    </div>
  )
}

type Window = '7' | '30' | '90'

export function DashboardPage() {
  const [days, setDays] = useState<Window>('30')
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
        <div className="ml-auto">
          <Segmented<Window>
            ariaLabel="Time window"
            options={[
              { id: '7', label: '7d' },
              { id: '30', label: '30d' },
              { id: '90', label: '90d' },
            ]}
            value={days}
            onChange={setDays}
          />
        </div>
      </PageTitle>

      {/* Hero band: the three numbers that matter */}
      <div
        className="relative mt-6 overflow-hidden rounded-3xl border border-line p-6 sm:p-8"
        style={{
          background:
            'radial-gradient(42rem 20rem at 12% -30%, #dcd7f6 0%, rgba(220,215,246,0) 60%), radial-gradient(40rem 22rem at 85% -20%, #f8ddc2 0%, rgba(248,221,194,0) 55%), #fffefb',
        }}
      >
        <div className="grid gap-6 sm:grid-cols-3">
          <HeroStat
            label="Notes processed"
            value={String(data.notes_processed)}
            hint={`last ${data.days} days`}
          />
          <HeroStat
            label="Acceptance rate"
            value={percent(data.acceptance_rate)}
            hint={
              data.override_rate != null
                ? `override rate ${percent(data.override_rate)}`
                : 'no decisions yet'
            }
          />
          <HeroStat
            label="Waiting for review"
            value={String(data.review_backlog)}
            hint="current backlog"
          />
        </div>
      </div>

      {/* Throughput */}
      <section className="mt-10">
        <MicroLabel>Throughput</MicroLabel>
        <div className="mt-3 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
          <Card className="p-5">
            <MicroLabel>Runs per day</MicroLabel>
            <div className="mt-3 h-52">
              <ResponsiveContainer>
                <AreaChart
                  data={data.runs_per_day}
                  margin={{ top: 8, right: 8, bottom: 0, left: -24 }}
                >
                  <defs>
                    <linearGradient id="runsFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={MARK_COLOR} stopOpacity={0.22} />
                      <stop offset="100%" stopColor={MARK_COLOR} stopOpacity={0} />
                    </linearGradient>
                  </defs>
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
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke={MARK_COLOR}
                    strokeWidth={2}
                    fill="url(#runsFill)"
                    dot={{ r: 3, fill: MARK_COLOR, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <div className="grid grid-cols-2 content-start gap-3">
            <MetricCard
              label="Avg processing"
              value={
                data.average_processing_ms != null
                  ? `${(data.average_processing_ms / 1000).toFixed(1)}s`
                  : '—'
              }
            />
            <MetricCard label="Suggestions" value={String(data.suggestions_made)} delay={40} />
            <MetricCard
              label="Failed runs"
              value={String(failures.reduce((n, [, c]) => n + c, 0))}
              hint={failures.map(([code, c]) => `${code}: ${c}`).join(', ') || undefined}
              delay={80}
            />
            <MetricCard
              label="AI calls"
              value={String(data.ai_usage.calls)}
              hint={`cache hits ${percent(data.ai_usage.cache_hit_rate)} · tokens ${
                data.ai_usage.input_tokens
              }/${data.ai_usage.output_tokens}`}
              delay={120}
            />
          </div>
        </div>
      </section>

      {/* Quality */}
      <section className="mt-10">
        <MicroLabel>Quality</MicroLabel>
        <div className="mt-3 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
          <Card className="p-5">
            <div className="flex items-baseline justify-between gap-3">
              <MicroLabel>Acceptance rate by confidence</MicroLabel>
              <span className="text-xs text-ink-faint">High should beat Low</span>
            </div>
            <div className="mt-3 h-52">
              <ResponsiveContainer>
                <BarChart
                  data={confidenceRates}
                  margin={{ top: 18, right: 8, bottom: 0, left: -24 }}
                >
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
                    contentStyle={TOOLTIP_STYLE}
                  />
                  <Bar dataKey="percent" fill={MARK_COLOR} radius={[5, 5, 0, 0]} maxBarSize={44}>
                    <LabelList
                      dataKey="percent"
                      position="top"
                      formatter={(value) => (value == null ? 'n/a' : `${String(value)}%`)}
                      style={{ fontSize: 12, fill: '#1c1917', fontWeight: 600 }}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <div className="grid grid-cols-2 content-start gap-3">
            <MetricCard label="HCCs captured" value={String(data.hccs_captured)} />
            <MetricCard
              label="Unsupported caught"
              value={String(data.unsupported_codes_caught)}
              delay={40}
            />
            <MetricCard
              label="Missed HCCs found"
              value={String(data.missed_hccs_found)}
              delay={80}
            />
            <MetricCard label="Override rate" value={percent(data.override_rate)} delay={120} />
          </div>
        </div>
      </section>

      {/* Backlog */}
      <section className="mt-10">
        <MicroLabel>Waiting for review</MicroLabel>
        {backlog.data?.items.length === 0 && (
          <p className="mt-2.5 text-sm text-ink-faint">Nothing waiting — the queue is clear.</p>
        )}
        <ul className="mt-3 space-y-2">
          {backlog.data?.items.map((run, index) => (
            <li key={run.id} className="anim-in" style={{ animationDelay: `${index * 40}ms` }}>
              <Link
                to={`/runs/${run.id}`}
                className="flex flex-wrap items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-3 text-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-12px_rgba(28,25,23,0.18)] motion-reduce:transition-none"
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
