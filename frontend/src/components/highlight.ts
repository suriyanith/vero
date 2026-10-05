// Pure helpers behind the evidence highlighter (separate file so the
// component module only exports components, keeping fast refresh happy).

export interface EvidenceSpan {
  start: number
  end: number
  conditionId: number
}

// One background per condition, cycled. Text stays dark for contrast.
export const HIGHLIGHT_PALETTE = [
  'bg-yellow-200',
  'bg-green-200',
  'bg-sky-200',
  'bg-pink-200',
  'bg-orange-200',
  'bg-violet-200',
  'bg-lime-200',
  'bg-cyan-200',
]

export function paletteFor(conditionIds: number[]): Map<number, string> {
  const ordered = [...new Set(conditionIds)].sort((a, b) => a - b)
  return new Map(ordered.map((id, i) => [id, HIGHLIGHT_PALETTE[i % HIGHLIGHT_PALETTE.length]]))
}

export interface Segment {
  start: number
  end: number
  conditionIds: number[]
}

export function segment(textLength: number, spans: EvidenceSpan[]): Segment[] {
  const boundaries = new Set([0, textLength])
  for (const span of spans) {
    boundaries.add(Math.max(0, span.start))
    boundaries.add(Math.min(textLength, span.end))
  }
  const points = [...boundaries].sort((a, b) => a - b)
  const segments: Segment[] = []
  for (let i = 0; i < points.length - 1; i++) {
    const [start, end] = [points[i], points[i + 1]]
    const ids = spans.filter((s) => s.start <= start && s.end >= end).map((s) => s.conditionId)
    segments.push({ start, end, conditionIds: [...new Set(ids)] })
  }
  return segments
}
