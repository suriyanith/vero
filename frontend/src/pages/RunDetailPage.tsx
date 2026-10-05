import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import type { RunDetail, Suggestion } from '../api/types'
import { CodeSearchModal } from '../components/CodeSearchModal'
import { EvidenceHighlighter } from '../components/EvidenceHighlighter'
import { paletteFor, type EvidenceSpan } from '../components/highlight'
import { StatusBadge } from '../components/badges'
import { SuggestionCard } from '../components/SuggestionCard'
import { useAcceptAllHigh, useDecide } from '../features/review/hooks'
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

  if (isPending) return <p className="text-gray-500">Loading…</p>
  if (isError || !run) return <p className="text-red-700">Run not found.</p>
  if (run.status === 'queued' || run.status === 'processing') {
    return (
      <div className="py-16 text-center">
        <StatusBadge status={run.status} />
        <p className="mt-3 text-gray-600">
          Processing “{run.note.title}”… this page updates itself.
        </p>
      </div>
    )
  }
  if (run.status === 'failed') {
    return (
      <div className="py-16 text-center">
        <StatusBadge status={run.status} />
        <p className="mt-3 text-red-700">
          {run.error_code}: {run.error_message}
        </p>
      </div>
    )
  }
  return <ReviewView run={run} />
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
  const notCoded = run.conditions.filter((c) => c.status !== 'active')

  const spans: EvidenceSpan[] = useMemo(
    () =>
      run.conditions.flatMap((c) =>
        c.quotes.map((q) => ({ start: q.start, end: q.end, conditionId: c.id })),
      ),
    [run.conditions],
  )
  const palette = paletteFor(run.conditions.map((c) => c.id))

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
        <h1 className="text-xl font-bold">{run.note.title}</h1>
        <StatusBadge status={run.status} />
        <button
          className="ml-auto text-xs text-gray-500 underline"
          onClick={() => setShowShortcuts(true)}
        >
          Keyboard shortcuts (?)
        </button>
      </div>

      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        {/* Left: the note with highlighted evidence */}
        <section
          aria-label="Note with highlighted evidence"
          className="max-h-[75vh] overflow-y-auto rounded-lg border border-gray-200 bg-white p-4"
        >
          <EvidenceHighlighter
            text={run.note.text}
            spans={spans}
            activeConditionId={hoveredCondition}
            onHoverCondition={setHoveredCondition}
          />
        </section>

        {/* Right: suggestions */}
        <section aria-label="Suggested codes" className="space-y-4">
          {run.suggestions.length === 0 && (
            <p className="text-gray-500">No codes suggested for this note.</p>
          )}

          {high.length > 0 && (
            <div>
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">High confidence</h2>
                {high.some((s) => !s.latest_decision) && (
                  <button
                    className="rounded bg-green-600 px-3 py-1 text-sm font-medium text-white hover:bg-green-700"
                    onClick={() => acceptHigh.mutate()}
                  >
                    Accept all High
                  </button>
                )}
              </div>
              <div className="mt-2 space-y-3">
                {high.map((s) => (
                  <SuggestionCard key={s.id} {...cardProps(s)} />
                ))}
              </div>
            </div>
          )}

          {needsReview.length > 0 && (
            <div>
              <h2 className="font-semibold">Needs review</h2>
              <div className="mt-2 space-y-3">
                {needsReview.map((s) => (
                  <SuggestionCard key={s.id} {...cardProps(s)} />
                ))}
              </div>
            </div>
          )}

          {notCoded.length > 0 && (
            <div>
              <h2 className="font-semibold">Not coded</h2>
              <ul className="mt-2 space-y-2">
                {notCoded.map((c) => (
                  <li key={c.id} className="rounded border border-gray-200 bg-white p-2 text-sm">
                    <span
                      className={`mr-2 inline-block h-3 w-3 rounded-sm align-middle ${
                        palette.get(c.id) ?? ''
                      }`}
                    />
                    <span className="font-medium">{c.label}</span>
                    <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                      {c.status.replaceAll('_', ' ')}
                    </span>
                    {c.quotes[0] && (
                      <span className="ml-2 italic text-gray-500">“{c.quotes[0].text}”</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      <footer className="mt-6 border-t border-gray-200 pt-3 text-xs text-gray-500">
        model {run.model_name || '—'} · prompts{' '}
        {Object.entries(run.prompt_versions)
          .map(([k, v]) => `${k} ${v}`)
          .join(', ') || '—'}{' '}
        · {run.duration_ms ?? '—'} ms · tokens {run.input_tokens}/{run.output_tokens} · dropped
        quotes {run.dropped_quotes}
      </footer>

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
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          role="dialog"
          aria-label="Keyboard shortcuts"
          onClick={() => setShowShortcuts(false)}
        >
          <div className="rounded-lg bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-semibold">Keyboard shortcuts</h2>
            <table className="mt-3 text-sm">
              <tbody>
                {SHORTCUTS.map(([key, what]) => (
                  <tr key={key}>
                    <td className="pr-6 font-mono text-gray-800">{key}</td>
                    <td className="text-gray-600">{what}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              className="mt-4 rounded border border-gray-300 px-3 py-1 text-sm"
              onClick={() => setShowShortcuts(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-label={`Reject ${suggestion.display_code}`}
      onClick={onCancel}
    >
      <div
        className="w-full max-w-md rounded-lg bg-white p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-semibold">
          Reject <span className="font-mono">{suggestion.display_code}</span>
        </h2>
        <label className="mt-3 block text-sm">
          Reason (optional)
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            autoFocus
            className="mt-1 w-full rounded border border-gray-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </label>
        <div className="mt-3 flex justify-end gap-2">
          <button className="rounded border border-gray-300 px-3 py-1 text-sm" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="rounded bg-red-600 px-3 py-1 text-sm font-medium text-white hover:bg-red-700"
            onClick={() => onConfirm(reason)}
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  )
}
