import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '../api/client'
import { Card as UICard, MicroLabel, PageTitle } from '../components/ui'

interface EvalRunListItem {
  id: string
  created_at: string
  split: string
  mode: string
  model_name: string
  provisional: boolean
}

interface PRF {
  precision: number | null
  recall: number | null
  f1: number | null
}

interface EvalRunDetail extends EvalRunListItem {
  pipeline_version: string
  prompt_versions: Record<string, string>
  git_sha: string
  metrics: {
    coding?: {
      code_level: PRF
      hcc_level: PRF
      category_level: PRF
      accuracy_by_confidence: Record<string, number | null>
      hard_cases: Record<string, { total: number; correctly_not_coded: number; accuracy: number }>
      evidence_integrity: Record<string, number>
      operational: Record<string, number | null>
    }
    audit?: {
      overall_accuracy: number | null
      per_verdict_accuracy: Record<string, number>
      confusion: Record<string, number>
      unsupported_caught_rate: number | null
      supported_wrongly_flagged_rate: number | null
    }
  }
  per_note_results: { note: string; predicted?: string[]; gold?: string[]; failed?: boolean }[]
}

const pct = (value: number | null | undefined) =>
  value == null ? '—' : `${Math.round(value * 100)}%`

function Card({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <UICard className="p-4">
      <MicroLabel>{label}</MicroLabel>
      <p
        className={`mt-1.5 text-2xl font-semibold tracking-tight tabular-nums ${
          warn ? 'text-[#9a2c21]' : ''
        }`}
      >
        {value}
      </p>
    </UICard>
  )
}

export function EvaluationPage() {
  const runs = useQuery({
    queryKey: ['eval-runs'],
    queryFn: () => api<EvalRunListItem[]>('/eval/runs'),
    retry: false,
  })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const activeId = selectedId ?? runs.data?.[0]?.id ?? null
  const detail = useQuery({
    queryKey: ['eval-run', activeId],
    queryFn: () => api<EvalRunDetail>(`/eval/runs/${activeId}`),
    enabled: activeId != null,
  })

  if (runs.isError) {
    const forbidden = runs.error instanceof ApiError && runs.error.status === 403
    return (
      <p className="text-[#9a2c21]">
        {forbidden ? 'The evaluation page is admin-only.' : 'Could not load evaluations.'}
      </p>
    )
  }
  if (runs.isPending) return <p className="text-ink-faint">Loading…</p>
  if (runs.data.length === 0) {
    return (
      <p className="text-ink-faint">
        No evaluations yet. Run <code>make eval</code> after reviewing the answer key.
      </p>
    )
  }

  const coding = detail.data?.metrics.coding
  const audit = detail.data?.metrics.audit

  return (
    <div>
      <PageTitle title="Evaluation" />
      {detail.data?.provisional && (
        <p className="mt-2 rounded-xl bg-[#faf0d7] px-3 py-2 text-sm text-[#8a5a12]">
          Provisional: this evaluation ran against unreviewed labels.
        </p>
      )}

      {coding && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Card label="Code F1" value={pct(coding.code_level.f1)} />
            <Card label="Code precision" value={pct(coding.code_level.precision)} />
            <Card label="Code recall" value={pct(coding.code_level.recall)} />
            <Card label="HCC recall" value={pct(coding.hcc_level.recall)} />
            <Card label="Category F1" value={pct(coding.category_level.f1)} />
            <Card
              label="Unverified quotes shown"
              value={String(coding.evidence_integrity.unverified_quotes_shown)}
              warn={coding.evidence_integrity.unverified_quotes_shown > 0}
            />
            <Card
              label="Invalid codes shown"
              value={String(coding.evidence_integrity.invalid_codes_shown)}
              warn={coding.evidence_integrity.invalid_codes_shown > 0}
            />
            <Card label="Success rate" value={pct(coding.operational.success_rate)} />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-line bg-surface p-5 shadow-[0_1px_2px_rgba(28,25,23,0.04)]">
              <h2 className="text-sm font-semibold tracking-tight">Accuracy by confidence</h2>
              <table className="mt-2 w-full text-sm">
                <tbody>
                  {Object.entries(coding.accuracy_by_confidence).map(([level, accuracy]) => (
                    <tr key={level} className="border-t border-line">
                      <td className="py-1 capitalize">{level}</td>
                      <td className="py-1 text-right font-mono">{pct(accuracy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-xs text-ink-faint">
                High should clearly beat Low; if not, the confidence rules need work.
              </p>
            </section>

            <section className="rounded-2xl border border-line bg-surface p-5 shadow-[0_1px_2px_rgba(28,25,23,0.04)]">
              <h2 className="text-sm font-semibold tracking-tight">
                Hard cases (correctly left uncoded)
              </h2>
              <table className="mt-2 w-full text-sm">
                <tbody>
                  {Object.entries(coding.hard_cases).map(([reason, row]) => (
                    <tr key={reason} className="border-t border-line">
                      <td className="py-1">{reason.replaceAll('_', ' ')}</td>
                      <td className="py-1 text-right font-mono">
                        {row.correctly_not_coded}/{row.total} ({pct(row.accuracy)})
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        </>
      )}

      {audit && (
        <section className="mt-8 rounded-2xl border border-line bg-surface p-5 shadow-[0_1px_2px_rgba(28,25,23,0.04)]">
          <h2 className="text-sm font-semibold tracking-tight">Audit mode</h2>
          <div className="mt-2 grid grid-cols-3 gap-3">
            <Card label="Verdict accuracy" value={pct(audit.overall_accuracy)} />
            <Card label="Unsupported caught" value={pct(audit.unsupported_caught_rate)} />
            <Card
              label="Supported wrongly flagged"
              value={pct(audit.supported_wrongly_flagged_rate)}
            />
          </div>
          <table className="mt-3 w-full text-sm">
            <tbody>
              {Object.entries(audit.per_verdict_accuracy).map(([verdict, accuracy]) => (
                <tr key={verdict} className="border-t border-line">
                  <td className="py-1">{verdict.replaceAll('_', ' ')}</td>
                  <td className="py-1 text-right font-mono">{pct(accuracy)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="mt-6">
        <MicroLabel>Past evaluations</MicroLabel>
        <ul className="mt-2 space-y-1">
          {runs.data.map((run) => (
            <li key={run.id}>
              <button
                className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                  run.id === activeId
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
                onClick={() => setSelectedId(run.id)}
              >
                {new Date(run.created_at).toLocaleString()} — {run.mode} on {run.split} —{' '}
                {run.model_name}
                {run.provisional && <span className="ml-2 text-[#8a5a12]">provisional</span>}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
