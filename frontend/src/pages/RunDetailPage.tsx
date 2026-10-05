import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import type { Finding, RunDetail, Suggestion } from '../api/types'
import { AuditFindingsTable } from '../components/AuditFindingsTable'
import { CodeSearchModal } from '../components/CodeSearchModal'
import { DecisionHistory } from '../components/DecisionHistory'
import { EvidenceHighlighter } from '../components/EvidenceHighlighter'
import { paletteFor, type EvidenceSpan } from '../components/highlight'
import { StatusBadge } from '../components/badges'
import { SuggestionCard } from '../components/SuggestionCard'
import { Button, Card, Dialog, MicroLabel, inputClass } from '../components/ui'
import { useAcceptAllHigh, useDecide, useDecideFinding } from '../features/review/hooks'
import { useRun } from '../features/runs/hooks'

const SHORTCUTS: [string, string][] = [
  ['j / k', 'next / previous suggestion'],
  ['a', 'accept the focused suggestion'],
  ['r', 'reject the focused suggestion'],
  ['m', 'modify the focused suggestion'],
  ['?', 'show or hide this help'],
]

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const { data: run, isPending, isError } = useRun(runId)

  if (isPending) return <p className="text-ink-faint">Loading…</p>
  if (isError || !run) return <p className="text-[#9a2c21]">Run not found.</p>
  if (run.status === 'queued' || run.status === 'processing') {
    return (
      <Card className="mx-auto mt-16 max-w-md p-10 text-center">
        <StatusBadge status={run.status} />
        <p className="mt-4 font-display text-lg">Reading “{run.note.title}”</p>
        <p className="mt-1 text-sm text-ink-soft">This page updates itself.</p>
      </Card>
    )
  }
  if (run.status === 'failed') {
    return (
      <Card className="mx-auto mt-16 max-w-md p-10 text-center">
        <StatusBadge status={run.status} />
        <p className="mt-4 text-sm text-[#9a2c21]">
          {run.error_code}: {run.error_message}
        </p>
      </Card>
    )
  }
  return run.mode === 'audit' ? <AuditView run={run} /> : <ReviewView run={run} />
}

function RunFooter({ run }: { run: RunDetail }) {
  const prompts = Object.entries(run.prompt_versions)
    .map(([k, v]) => `${k} ${v}`)
    .join(', ')
  return (
    <footer className="mt-8 border-t border-line pt-3 text-xs text-ink-faint">
      model {run.model_name || '—'} · prompts {prompts || '—'} · {run.duration_ms ?? '—'} ms ·
      tokens {run.input_tokens}/{run.output_tokens} · dropped quotes {run.dropped_quotes}
    </footer>
  )
}

function NotePanel({
  run,
  spans,
  hovered,
  onHover,
}: {
  run: RunDetail
  spans: EvidenceSpan[]
  hovered: number | null
  onHover: (id: number | null) => void
}) {
  return (
    <section aria-label="Note with highlighted evidence" className="lg:sticky lg:top-24">
      <MicroLabel>The note</MicroLabel>
      <Card className="mt-2.5 max-h-[72vh] overflow-y-auto p-6">
        <EvidenceHighlighter
          text={run.note.text}
          spans={spans}
          activeConditionId={hovered}
          onHoverCondition={onHover}
        />
      </Card>
    </section>
  )
}

function NotCodedList({ run }: { run: RunDetail }) {
  const notCoded = run.conditions.filter((c) => c.status !== 'active')
  const palette = paletteFor(run.conditions.map((c) => c.id))
  if (notCoded.length === 0) return null
  return (
    <div>
      <MicroLabel>Not coded — and why</MicroLabel>
      <ul className="mt-2.5 space-y-1.5">
        {notCoded.map((c) => (
          <li key={c.id} className="flex flex-wrap items-baseline gap-2 text-sm">
            <span
              aria-hidden
              className={`inline-block h-2.5 w-2.5 translate-y-px rounded-[3px] ${
                palette.get(c.id) ?? ''
              }`}
            />
            <span className="font-medium">{c.label}</span>
            <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-ink-soft">
              {c.status.replaceAll('_', ' ')}
            </span>
            {c.quotes[0] && (
              <span className="font-display italic text-ink-faint">“{c.quotes[0].text}”</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ReviewView({ run }: { run: RunDetail }) {
  const decide = useDecide(run.id)
  const acceptHigh = useAcceptAllHigh(run.id)
  const [hoveredCondition, setHoveredCondition] = useState<number | null>(null)
  const [focusIndex, setFocusIndex] = useState(0)
  const [rejecting, setRejecting] = useState<Suggestion | null>(null)
  const [modifying, setModifying] = useState<Suggestion | null>(null)
  const [showShortcuts, setShowShortcuts] = useState(false)

  const high = useMemo(
    () => run.suggestions.filter((s) => s.confidence === 'high'),
    [run.suggestions],
  )
  const needsReview = useMemo(
    () => run.suggestions.filter((s) => s.confidence !== 'high'),
    [run.suggestions],
  )
  const ordered = useMemo(() => [...high, ...needsReview], [high, needsReview])

  const spans: EvidenceSpan[] = useMemo(
    () =>
      run.conditions.flatMap((c) =>
        c.quotes.map((q) => ({ start: q.start, end: q.end, conditionId: c.id })),
      ),
    [run.conditions],
  )

  const scrollToEvidence = (conditionId: number | null) => {
    if (conditionId == null) return
    document
      .querySelector(`mark[data-condition-id="${conditionId}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
      if (rejecting || modifying) return
      const focused = ordered[focusIndex]
      switch (event.key) {
        case 'j':
          setFocusIndex((i) => Math.min(i + 1, ordered.length - 1))
          break
        case 'k':
          setFocusIndex((i) => Math.max(i - 1, 0))
          break
        case 'a':
          if (focused) decide.mutate({ suggestionId: focused.id, input: { action: 'accept' } })
          break
        case 'r':
          if (focused) setRejecting(focused)
          break
        case 'm':
          if (focused) setModifying(focused)
          break
        case '?':
          setShowShortcuts((v) => !v)
          break
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [ordered, focusIndex, rejecting, modifying, decide])

  const cardProps = (suggestion: Suggestion) => ({
    suggestion,
    focused: ordered[focusIndex]?.id === suggestion.id,
    onAccept: () => decide.mutate({ suggestionId: suggestion.id, input: { action: 'accept' } }),
    onReject: () => setRejecting(suggestion),
    onModify: () => setModifying(suggestion),
    onClickEvidence: () => scrollToEvidence(suggestion.condition_id ?? null),
  })

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-2xl font-semibold tracking-tight">{run.note.title}</h1>
        <StatusBadge status={run.status} />
        <button
          className="ml-auto text-xs text-ink-faint hover:text-ink"
          onClick={() => setShowShortcuts(true)}
        >
          Keyboard shortcuts <kbd className="rounded border border-line-strong px-1">?</kbd>
        </button>
      </div>

      <div className="mt-6 grid items-start gap-8 lg:grid-cols-[1fr_1.1fr]">
        <NotePanel
          run={run}
          spans={spans}
          hovered={hoveredCondition}
          onHover={setHoveredCondition}
        />

        <section aria-label="Suggested codes" className="space-y-7">
          {run.suggestions.length === 0 && (
            <Card className="p-8 text-center text-sm text-ink-soft">
              No codes suggested for this note.
            </Card>
          )}

          {high.length > 0 && (
            <div>
              <div className="flex items-center justify-between">
                <MicroLabel>High confidence</MicroLabel>
                {high.some((s) => !s.latest_decision) && (
                  <Button variant="primary" size="sm" onClick={() => acceptHigh.mutate()}>
                    Accept all High
                  </Button>
                )}
              </div>
              <div className="mt-2.5 space-y-3">
                {high.map((s) => (
                  <SuggestionCard key={s.id} {...cardProps(s)} />
                ))}
              </div>
            </div>
          )}

          {needsReview.length > 0 && (
            <div>
              <MicroLabel>Needs review</MicroLabel>
              <div className="mt-2.5 space-y-3">
                {needsReview.map((s) => (
                  <SuggestionCard key={s.id} {...cardProps(s)} />
                ))}
              </div>
            </div>
          )}

          <NotCodedList run={run} />
        </section>
      </div>

      <DecisionHistory runId={run.id} />
      <RunFooter run={run} />

      {rejecting && (
        <RejectDialog
          suggestion={rejecting}
          onCancel={() => setRejecting(null)}
          onConfirm={(reason) => {
            decide.mutate({ suggestionId: rejecting.id, input: { action: 'reject', reason } })
            setRejecting(null)
          }}
        />
      )}

      {modifying && (
        <CodeSearchModal
          title={`Replace ${modifying.display_code}`}
          onClose={() => setModifying(null)}
          onSelect={(code) => {
            decide.mutate({
              suggestionId: modifying.id,
              input: { action: 'modify', final_code: code.display_code },
            })
            setModifying(null)
          }}
        />
      )}

      {showShortcuts && (
        <Dialog label="Keyboard shortcuts" onClose={() => setShowShortcuts(false)}>
          <h2 className="font-display text-lg font-semibold tracking-tight">Keyboard shortcuts</h2>
          <table className="mt-4 w-full text-sm">
            <tbody>
              {SHORTCUTS.map(([key, what]) => (
                <tr key={key} className="border-t border-line first:border-t-0">
                  <td className="py-2 pr-6 font-mono text-[13px] text-ink">{key}</td>
                  <td className="py-2 text-ink-soft">{what}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Button className="mt-4" onClick={() => setShowShortcuts(false)}>
            Close
          </Button>
        </Dialog>
      )}
    </div>
  )
}

function AuditView({ run }: { run: RunDetail }) {
  const decideFinding = useDecideFinding(run.id)
  const [hoveredCondition, setHoveredCondition] = useState<number | null>(null)

  const spans: EvidenceSpan[] = useMemo(
    () =>
      run.conditions.flatMap((c) =>
        c.quotes.map((q) => ({ start: q.start, end: q.end, conditionId: c.id })),
      ),
    [run.conditions],
  )
  const submitted = run.findings.filter((f) => f.verdict !== 'MISSED_HCC')
  const missed = run.findings.filter((f) => f.verdict === 'MISSED_HCC')

  const act = (finding: Finding, action: 'accept' | 'reject') =>
    decideFinding.mutate({ findingId: finding.id, input: { action } })

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-2xl font-semibold tracking-tight">{run.note.title}</h1>
        <StatusBadge status={run.status} />
        <span className="rounded-full bg-ink px-2.5 py-0.5 text-xs font-medium text-paper">
          audit
        </span>
      </div>

      <div className="mt-6 grid items-start gap-8 lg:grid-cols-[1fr_1.2fr]">
        <NotePanel
          run={run}
          spans={spans}
          hovered={hoveredCondition}
          onHover={setHoveredCondition}
        />

        <section aria-label="Audit findings" className="space-y-7">
          <AuditFindingsTable
            title="Submitted codes"
            findings={submitted}
            onAccept={(f) => act(f, 'accept')}
            onReject={(f) => act(f, 'reject')}
          />
          <AuditFindingsTable
            title="Missed HCCs"
            findings={missed}
            onAccept={(f) => act(f, 'accept')}
            onReject={(f) => act(f, 'reject')}
          />
          <NotCodedList run={run} />
        </section>
      </div>

      <DecisionHistory runId={run.id} />
      <RunFooter run={run} />
    </div>
  )
}

function RejectDialog({
  suggestion,
  onCancel,
  onConfirm,
}: {
  suggestion: Suggestion
  onCancel: () => void
  onConfirm: (reason: string) => void
}) {
  const [reason, setReason] = useState('')
  return (
    <Dialog label={`Reject ${suggestion.display_code}`} onClose={onCancel}>
      <h2 className="font-display text-lg font-semibold tracking-tight">
        Reject <span className="font-mono">{suggestion.display_code}</span>
      </h2>
      <label className="mt-4 block text-sm font-medium">
        Reason <span className="font-normal text-ink-faint">(optional)</span>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          autoFocus
          className={`mt-1.5 w-full ${inputClass}`}
        />
      </label>
      <div className="mt-4 flex justify-end gap-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="reject" onClick={() => onConfirm(reason)}>
          Reject
        </Button>
      </div>
    </Dialog>
  )
}
