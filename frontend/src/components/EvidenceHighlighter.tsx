// Renders the note with each condition's evidence highlighted by character
// offsets. Overlapping quotes are split into segments so nothing is lost.
import { paletteFor, segment, type EvidenceSpan } from './highlight'

export function EvidenceHighlighter({
  text,
  spans,
  activeConditionId,
  onHoverCondition,
}: {
  text: string
  spans: EvidenceSpan[]
  activeConditionId?: number | null
  onHoverCondition?: (id: number | null) => void
}) {
  const palette = paletteFor(spans.map((s) => s.conditionId))
  return (
    <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-6">
      {segment(text.length, spans).map((seg) => {
        const slice = text.slice(seg.start, seg.end)
        if (seg.conditionIds.length === 0) {
          return <span key={seg.start}>{slice}</span>
        }
        const primary = seg.conditionIds[0]
        const isActive = activeConditionId != null && seg.conditionIds.includes(activeConditionId)
        return (
          <mark
            key={seg.start}
            id={`evidence-${primary}-${seg.start}`}
            data-condition-id={primary}
            className={`rounded-sm px-0.5 ${palette.get(primary) ?? ''} ${
              isActive ? 'ring-2 ring-gray-900' : ''
            }`}
            onMouseEnter={() => onHoverCondition?.(primary)}
            onMouseLeave={() => onHoverCondition?.(null)}
          >
            {slice}
          </mark>
        )
      })}
    </pre>
  )
}
