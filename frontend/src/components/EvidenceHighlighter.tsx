// Renders the note like a document sheet with each condition's evidence
// highlighted by character offsets. Overlaps split into segments.
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
    <pre className="m-0 whitespace-pre-wrap break-words font-sans text-[13.5px] leading-7 text-stone-800">
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
            className={`rounded-[4px] px-[3px] py-[1px] text-ink ${palette.get(primary) ?? ''} ${
              isActive ? 'ring-2 ring-ink/70' : ''
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
