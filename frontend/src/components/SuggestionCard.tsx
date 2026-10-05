import type { Suggestion } from '../api/types'
import { ConfidenceBadge, DecisionBadge, HccBadge, MeatChips } from './badges'
import { Button, Card } from './ui'

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
          {decision && <DecisionBadge action={decision.action} />}
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
          <p className="mt-3 border-t border-line pt-2.5 text-xs text-ink-faint">
            {decision.action === 'modify' && (
              <span className="mr-1 font-mono font-semibold text-ink">→ {decision.final_code}</span>
            )}
            by {decision.reviewer_name}
            {decision.reason && <span> — “{decision.reason}”</span>}
          </p>
        )}

        <div className="mt-3.5 flex gap-2">
          <Button variant="accept" size="sm" onClick={onAccept}>
            Accept
          </Button>
          <Button variant="reject" size="sm" onClick={onReject}>
            Reject
          </Button>
          <Button variant="modify" size="sm" onClick={onModify}>
            Modify
          </Button>
        </div>
      </article>
    </Card>
  )
}
