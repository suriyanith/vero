import { useState } from 'react'
import type { Suggestion } from '../api/types'
import { ConfidenceBadge, DecisionBadge, HccBadge, MeatChips } from './badges'
import { Button, Card } from './ui'

const RESOLVED_TINT: Record<string, string> = {
  accept: 'bg-[#eef7ef]',
  reject: 'bg-[#fdf1f0]',
  modify: 'bg-[#f1effc]',
}

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
  // "Change" re-opens the action buttons on an already-decided card; any new
  // decision (or an optimistic update) closes them again.
  const [changing, setChanging] = useState(false)
  // Reset "changing" whenever a new decision lands (render-phase adjustment,
  // the React-sanctioned alternative to a setState-in-effect cascade).
  const decisionKey = decision ? `${decision.action}:${decision.created_at}` : ''
  const [prevDecisionKey, setPrevDecisionKey] = useState(decisionKey)
  if (prevDecisionKey !== decisionKey) {
    setPrevDecisionKey(decisionKey)
    setChanging(false)
  }

  const showButtons = !decision || changing

  return (
    <Card className={`p-4 ${focused ? 'ring-2 ring-accent' : ''}`}>
      <article
        data-testid={`suggestion-${suggestion.display_code}`}
        onMouseEnter={() => onHover?.(true)}
        onMouseLeave={() => onHover?.(false)}
      >
        <div className="flex flex-wrap items-center gap-2">
          <button
            className="font-mono text-lg font-bold tracking-tight hover:text-accent"
            onClick={onClickEvidence}
            title="Scroll to evidence"
          >
            {suggestion.display_code}
          </button>
          <ConfidenceBadge level={suggestion.confidence} reasons={suggestion.confidence_reasons} />
          <HccBadge number={suggestion.hcc_number ?? null} label={suggestion.hcc_label} />
          <MeatChips meat={suggestion.meat} />
        </div>
        <p className="mt-1.5 text-sm text-stone-700">{suggestion.description}</p>

        {suggestion.evidence.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {suggestion.evidence.map((quote) => (
              <li
                key={`${quote.start}-${quote.end}`}
                className="border-l-2 border-line-strong pl-3 font-display text-[13.5px] italic leading-6 text-ink-soft"
              >
                “{quote.text}”
              </li>
            ))}
          </ul>
        )}

        {suggestion.rationale && (
          <p className="mt-2.5 text-xs leading-5 text-ink-faint">{suggestion.rationale}</p>
        )}

        {suggestion.flags.length > 0 && (
          <p className="mt-1.5 text-xs font-medium text-[#8a5a12]">
            flags: {suggestion.flags.join(', ')}
          </p>
        )}

        {decision && (
          <div
            className={`mt-3.5 flex flex-wrap items-center gap-2 rounded-xl px-3 py-2 ${
              RESOLVED_TINT[decision.action] ?? 'bg-stone-100'
            }`}
          >
            <DecisionBadge action={decision.action} />
            {decision.action === 'modify' && decision.final_code && (
              <span className="font-mono text-sm font-semibold">→ {decision.final_code}</span>
            )}
            <span className="text-xs text-ink-soft">by {decision.reviewer_name}</span>
            {decision.reason && (
              <span className="truncate text-xs text-ink-faint">— “{decision.reason}”</span>
            )}
            {!changing && (
              <button
                className="ml-auto rounded-full px-2.5 py-1 text-xs font-medium text-ink-soft transition-colors hover:bg-ink/5 hover:text-ink"
                onClick={() => setChanging(true)}
              >
                Change
              </button>
            )}
          </div>
        )}

        {showButtons && (
          <div className="mt-3.5 flex flex-wrap items-center gap-2">
            <Button variant="accept" size="sm" onClick={onAccept}>
              Accept
            </Button>
            <Button variant="reject" size="sm" onClick={onReject}>
              Reject
            </Button>
            <Button variant="modify" size="sm" onClick={onModify}>
              Modify
            </Button>
            {changing && (
              <Button variant="ghost" size="sm" onClick={() => setChanging(false)}>
                Cancel
              </Button>
            )}
          </div>
        )}
      </article>
    </Card>
  )
}
