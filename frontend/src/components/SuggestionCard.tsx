import type { Suggestion } from '../api/types'
import { ConfidenceBadge, DecisionBadge, HccBadge, MeatChips } from './badges'

export function SuggestionCard({
  suggestion,
  focused,
  onAccept,
  onReject,
  onModify,
  onHover,
  onClickEvidence,
}: {
  suggestion: Suggestion
  focused?: boolean
  onAccept: () => void
  onReject: () => void
  onModify: () => void
  onHover?: (hovering: boolean) => void
  onClickEvidence?: () => void
}) {
  const decision = suggestion.latest_decision
  return (
    <article
      data-testid={`suggestion-${suggestion.display_code}`}
      className={`rounded-lg border bg-white p-3 shadow-sm ${
        focused ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'
      }`}
      onMouseEnter={() => onHover?.(true)}
      onMouseLeave={() => onHover?.(false)}
    >
      <div className="flex flex-wrap items-center gap-2">
        <button
          className="font-mono text-lg font-bold hover:underline"
          onClick={onClickEvidence}
          title="Scroll to evidence"
        >
          {suggestion.display_code}
        </button>
        <ConfidenceBadge level={suggestion.confidence} reasons={suggestion.confidence_reasons} />
        <HccBadge number={suggestion.hcc_number ?? null} label={suggestion.hcc_label} />
        <MeatChips meat={suggestion.meat} />
        {decision && <DecisionBadge action={decision.action} />}
      </div>
      <p className="mt-1 text-sm text-gray-800">{suggestion.description}</p>

      {suggestion.evidence.length > 0 && (
        <ul className="mt-2 space-y-1">
          {suggestion.evidence.map((quote) => (
            <li
              key={`${quote.start}-${quote.end}`}
              className="border-l-2 border-gray-300 pl-2 text-sm italic text-gray-600"
            >
              “{quote.text}”
            </li>
          ))}
        </ul>
      )}

      {suggestion.rationale && <p className="mt-2 text-xs text-gray-500">{suggestion.rationale}</p>}

      {suggestion.flags.length > 0 && (
        <p className="mt-1 text-xs text-amber-700">flags: {suggestion.flags.join(', ')}</p>
      )}

      {decision ? (
        <p className="mt-2 text-xs text-gray-500">
          {decision.action === 'modify' && (
            <span className="mr-1 font-mono font-semibold">→ {decision.final_code}</span>
          )}
          by {decision.reviewer_name}
          {decision.reason && <span> — “{decision.reason}”</span>}
        </p>
      ) : null}

      <div className="mt-3 flex gap-2">
        <button
          className="rounded bg-green-600 px-3 py-1 text-sm font-medium text-white hover:bg-green-700"
          onClick={onAccept}
        >
          Accept
        </button>
        <button
          className="rounded bg-red-600 px-3 py-1 text-sm font-medium text-white hover:bg-red-700"
          onClick={onReject}
        >
          Reject
        </button>
        <button
          className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700"
          onClick={onModify}
        >
          Modify
        </button>
      </div>
    </article>
  )
}
