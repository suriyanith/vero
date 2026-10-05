import { useState } from 'react'
import type { Finding } from '../api/types'
import { DecisionBadge, VerdictBadge } from './badges'
import { Button, Card, MicroLabel } from './ui'

function FindingDecisionCell({
  finding,
  onAccept,
  onReject,
}: {
  finding: Finding
  onAccept: () => void
  onReject: () => void
}) {
  const decision = finding.latest_decision
  const [changing, setChanging] = useState(false)
  // Reset "changing" whenever a new decision lands (render-phase adjustment,
  // the React-sanctioned alternative to a setState-in-effect cascade).
  const decisionKey = decision ? `${decision.action}:${decision.created_at}` : ''
  const [prevDecisionKey, setPrevDecisionKey] = useState(decisionKey)
  if (prevDecisionKey !== decisionKey) {
    setPrevDecisionKey(decisionKey)
    setChanging(false)
  }

  if (decision && !changing) {
    return (
      <div className="text-xs text-ink-faint">
        <DecisionBadge action={decision.action} />
        <p className="mt-1.5">by {decision.reviewer_name}</p>
        <button
          className="mt-1 font-medium text-ink-soft underline-offset-2 hover:text-ink hover:underline"
          onClick={() => setChanging(true)}
        >
          Change
        </button>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      <Button variant="accept" size="sm" onClick={onAccept}>
        Accept
      </Button>
      <Button variant="reject" size="sm" onClick={onReject}>
        Reject
      </Button>
      {changing && (
        <Button variant="ghost" size="sm" onClick={() => setChanging(false)}>
          Cancel
        </Button>
      )}
    </div>
  )
}

// The audit verdict table: submitted codes first, then the missed-HCC
// two-way findings, each row with its own accept/reject decision.
export function AuditFindingsTable({
  title,
  findings,
  onAccept,
  onReject,
}: {
  title: string
  findings: Finding[]
  onAccept: (finding: Finding) => void
  onReject: (finding: Finding) => void
}) {
  if (findings.length === 0) return null
  return (
    <div>
      <h2 className="font-display text-lg font-semibold tracking-tight">{title}</h2>
      <Card className="mt-2.5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[38rem] border-collapse text-sm">
            <thead>
              <tr className="text-left">
                {['Code', 'Verdict', 'Reason & evidence', 'Suggested', 'Decision'].map((header) => (
                  <th key={header} className="px-4 py-3">
                    <MicroLabel>{header}</MicroLabel>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {findings.map((finding) => (
                <tr
                  key={finding.id}
                  data-testid={`finding-${finding.submitted_code || finding.suggested_code}`}
                  className="border-t border-line align-top"
                >
                  <td className="px-4 py-3 font-mono font-semibold">
                    {finding.submitted_code || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <VerdictBadge verdict={finding.verdict} />
                  </td>
                  <td className="px-4 py-3">
                    <p className="leading-6 text-stone-700">{finding.reason}</p>
                    {finding.evidence.map((quote) => (
                      <p
                        key={`${quote.start}-${quote.end}`}
                        className="mt-1.5 border-l-2 border-line-strong pl-3 font-display text-[13px] italic leading-5 text-ink-soft"
                      >
                        “{quote.text}”
                      </p>
                    ))}
                  </td>
                  <td className="px-4 py-3 font-mono">{finding.suggested_code || '—'}</td>
                  <td className="px-4 py-3">
                    <FindingDecisionCell
                      finding={finding}
                      onAccept={() => onAccept(finding)}
                      onReject={() => onReject(finding)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
