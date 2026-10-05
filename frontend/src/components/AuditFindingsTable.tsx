import type { Finding } from '../api/types'
import { DecisionBadge, VerdictBadge } from './badges'

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
      <h2 className="font-semibold">{title}</h2>
      <table className="mt-2 w-full border-collapse overflow-hidden rounded-lg bg-white text-sm shadow-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <th className="px-3 py-2">Code</th>
            <th className="px-3 py-2">Verdict</th>
            <th className="px-3 py-2">Reason &amp; evidence</th>
            <th className="px-3 py-2">Suggested</th>
            <th className="px-3 py-2">Decision</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((finding) => (
            <tr
              key={finding.id}
              data-testid={`finding-${finding.submitted_code || finding.suggested_code}`}
              className="border-b border-gray-100 align-top"
            >
              <td className="px-3 py-2 font-mono font-semibold">{finding.submitted_code || '—'}</td>
              <td className="px-3 py-2">
                <VerdictBadge verdict={finding.verdict} />
              </td>
              <td className="px-3 py-2">
                <p className="text-gray-800">{finding.reason}</p>
                {finding.evidence.map((quote) => (
                  <p
                    key={`${quote.start}-${quote.end}`}
                    className="mt-1 border-l-2 border-gray-300 pl-2 text-xs italic text-gray-500"
                  >
                    “{quote.text}”
                  </p>
                ))}
              </td>
              <td className="px-3 py-2 font-mono">{finding.suggested_code || '—'}</td>
              <td className="px-3 py-2">
                {finding.latest_decision ? (
                  <div className="text-xs text-gray-600">
                    <DecisionBadge action={finding.latest_decision.action} />
                    <p className="mt-1">by {finding.latest_decision.reviewer_name}</p>
                  </div>
                ) : (
                  <div className="flex gap-1">
                    <button
                      className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700"
                      onClick={() => onAccept(finding)}
                    >
                      Accept
                    </button>
                    <button
                      className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700"
                      onClick={() => onReject(finding)}
                    >
                      Reject
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
