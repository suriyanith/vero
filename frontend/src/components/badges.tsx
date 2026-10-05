// Small labeled badges. Color never carries meaning alone: every badge has text.

const CONFIDENCE_STYLES: Record<string, string> = {
  high: 'bg-green-100 text-green-800 border-green-300',
  medium: 'bg-amber-100 text-amber-800 border-amber-300',
  low: 'bg-red-100 text-red-800 border-red-300',
}

export function ConfidenceBadge({ level, reasons }: { level: string; reasons?: string[] }) {
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${
        CONFIDENCE_STYLES[level] ?? 'bg-gray-100 text-gray-700 border-gray-300'
      }`}
      title={reasons?.join('; ')}
    >
      {level} confidence
    </span>
  )
}

const STATUS_STYLES: Record<string, string> = {
  queued: 'bg-gray-100 text-gray-700',
  processing: 'bg-blue-100 text-blue-800',
  ready_for_review: 'bg-amber-100 text-amber-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-700'
      }`}
    >
      {status.replaceAll('_', ' ')}
    </span>
  )
}

export function HccBadge({ number, label }: { number: number | null; label?: string | null }) {
  if (number == null) {
    return (
      <span className="inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
        no HCC
      </span>
    )
  }
  return (
    <span
      className="inline-block rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800"
      title={label ?? undefined}
    >
      HCC {number}
    </span>
  )
}

export function MeatChips({ meat }: { meat: string[] }) {
  if (meat.length === 0) {
    return <span className="text-xs text-red-700">no MEAT</span>
  }
  return (
    <span className="inline-flex gap-1">
      {meat.map((m) => (
        <span key={m} className="rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-800">
          {m}
        </span>
      ))}
    </span>
  )
}

export function DecisionBadge({ action }: { action: string }) {
  const styles: Record<string, string> = {
    accept: 'bg-green-600 text-white',
    reject: 'bg-red-600 text-white',
    modify: 'bg-blue-600 text-white',
  }
  const labels: Record<string, string> = {
    accept: 'accepted',
    reject: 'rejected',
    modify: 'modified',
  }
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${
        styles[action] ?? 'bg-gray-500 text-white'
      }`}
    >
      {labels[action] ?? action}
    </span>
  )
}

const VERDICT_STYLES: Record<string, string> = {
  SUPPORTED: 'bg-green-100 text-green-800 border-green-300',
  WEAK_SUPPORT: 'bg-amber-100 text-amber-800 border-amber-300',
  SPECIFICITY_MISMATCH: 'bg-blue-100 text-blue-800 border-blue-300',
  NOT_SUPPORTED: 'bg-red-100 text-red-800 border-red-300',
  INVALID_CODE: 'bg-red-100 text-red-800 border-red-300',
  MISSED_HCC: 'bg-purple-100 text-purple-800 border-purple-300',
}

export function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold ${
        VERDICT_STYLES[verdict] ?? 'bg-gray-100 text-gray-700 border-gray-300'
      }`}
    >
      {verdict.replaceAll('_', ' ')}
    </span>
  )
}
