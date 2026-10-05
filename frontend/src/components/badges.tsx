// Tinted pills with a status dot. Color never carries meaning alone: every
// badge has text, and the palette stays soft so the ink type leads.

function Pill({
  tint,
  dot,
  title,
  children,
}: {
  tint: string
  dot?: string
  title?: string
  children: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${tint}`}
      title={title}
    >
      {dot && <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${dot}`} />}
      {children}
    </span>
  )
}

const CONFIDENCE: Record<string, [string, string]> = {
  high: ['bg-[#e3f1e5] text-[#1b5e2f]', 'bg-[#2e8b4a]'],
  medium: ['bg-[#faf0d7] text-[#8a5a12]', 'bg-[#d19a2f]'],
  low: ['bg-[#fbe7e5] text-[#9a2c21]', 'bg-[#cd5247]'],
}

export function ConfidenceBadge({ level, reasons }: { level: string; reasons?: string[] }) {
  const [tint, dot] = CONFIDENCE[level] ?? ['bg-stone-100 text-ink-soft', 'bg-stone-400']
  return (
    <Pill tint={tint} dot={dot} title={reasons?.join('; ')}>
      {`${level} confidence`}
    </Pill>
  )
}

const STATUS: Record<string, [string, string]> = {
  queued: ['bg-stone-100 text-ink-soft', 'bg-stone-400'],
  processing: ['bg-accent-soft text-accent', 'bg-accent'],
  ready_for_review: ['bg-[#faf0d7] text-[#8a5a12]', 'bg-[#d19a2f]'],
  completed: ['bg-[#e3f1e5] text-[#1b5e2f]', 'bg-[#2e8b4a]'],
  failed: ['bg-[#fbe7e5] text-[#9a2c21]', 'bg-[#cd5247]'],
}

export function StatusBadge({ status }: { status: string }) {
  const [tint, dot] = STATUS[status] ?? ['bg-stone-100 text-ink-soft', 'bg-stone-400']
  return (
    <Pill tint={tint} dot={dot}>
      {status.replaceAll('_', ' ')}
    </Pill>
  )
}

export function HccBadge({ number, label }: { number: number | null; label?: string | null }) {
  if (number == null) {
    return <Pill tint="bg-stone-100 text-ink-faint">no HCC</Pill>
  }
  return (
    <Pill tint="bg-accent-soft text-accent" title={label ?? undefined}>
      {`HCC ${number}`}
    </Pill>
  )
}

export function MeatChips({ meat }: { meat: string[] }) {
  if (meat.length === 0) {
    return <Pill tint="bg-[#fbe7e5] text-[#9a2c21]">no MEAT</Pill>
  }
  return (
    <span className="inline-flex gap-1">
      {meat.map((m) => (
        <span
          key={m}
          className="rounded-full bg-[#e9eef5] px-2 py-0.5 text-xs font-medium text-[#3b5572]"
        >
          {m}
        </span>
      ))}
    </span>
  )
}

const DECISION: Record<string, [string, string, string]> = {
  accept: ['bg-[#e3f1e5] text-[#1b5e2f]', 'bg-[#2e8b4a]', 'accepted'],
  reject: ['bg-[#fbe7e5] text-[#9a2c21]', 'bg-[#cd5247]', 'rejected'],
  modify: ['bg-accent-soft text-accent', 'bg-accent', 'modified'],
}

export function DecisionBadge({ action }: { action: string }) {
  const [tint, dot, label] = DECISION[action] ?? [
    'bg-stone-100 text-ink-soft',
    'bg-stone-400',
    action,
  ]
  return (
    <Pill tint={tint} dot={dot}>
      {label}
    </Pill>
  )
}

const VERDICT: Record<string, [string, string]> = {
  SUPPORTED: ['bg-[#e3f1e5] text-[#1b5e2f]', 'bg-[#2e8b4a]'],
  WEAK_SUPPORT: ['bg-[#faf0d7] text-[#8a5a12]', 'bg-[#d19a2f]'],
  SPECIFICITY_MISMATCH: ['bg-[#e3ecf8] text-[#2a4e8b]', 'bg-[#4472ba]'],
  NOT_SUPPORTED: ['bg-[#fbe7e5] text-[#9a2c21]', 'bg-[#cd5247]'],
  INVALID_CODE: ['bg-[#fbe7e5] text-[#9a2c21]', 'bg-[#cd5247]'],
  MISSED_HCC: ['bg-accent-soft text-accent', 'bg-accent'],
}

export function VerdictBadge({ verdict }: { verdict: string }) {
  const [tint, dot] = VERDICT[verdict] ?? ['bg-stone-100 text-ink-soft', 'bg-stone-400']
  return (
    <Pill tint={tint} dot={dot}>
      {verdict.replaceAll('_', ' ')}
    </Pill>
  )
}
