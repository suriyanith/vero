// Replay a precomputed Vero run: highlight evidence, render code cards and
// audit verdicts. Pure static — the JSON was exported from a real run.
import demo from './demo.json'

const noteEl = document.getElementById('note-text')
const suggestionsEl = document.getElementById('suggestions')
const notCodedEl = document.getElementById('not-coded')
const findingsBody = document.querySelector('#findings tbody')

// --- note with highlights -------------------------------------------------
const spans = demo.conditions.flatMap((c) =>
  c.quotes.map((q) => ({ start: q.start, end: q.end, conditionId: c.id })),
)
const boundaries = new Set([0, demo.note.text.length])
for (const s of spans) {
  boundaries.add(s.start)
  boundaries.add(s.end)
}
const points = [...boundaries].sort((a, b) => a - b)
for (let i = 0; i < points.length - 1; i++) {
  const [start, end] = [points[i], points[i + 1]]
  const slice = demo.note.text.slice(start, end)
  const owner = spans.find((s) => s.start <= start && s.end >= end)
  if (!owner) {
    noteEl.append(slice)
  } else {
    const mark = document.createElement('mark')
    mark.textContent = slice
    mark.className = `c${((owner.conditionId - 1) % 5) + 1}`
    mark.dataset.conditionId = owner.conditionId
    noteEl.append(mark)
  }
}

function setActive(conditionId, on) {
  for (const mark of noteEl.querySelectorAll('mark')) {
    mark.classList.toggle(
      'active',
      on && Number(mark.dataset.conditionId) === Number(conditionId),
    )
  }
}

// --- suggestion cards -----------------------------------------------------
const badge = (text, cls) => `<span class="badge ${cls}">${text}</span>`

for (const s of demo.suggestions) {
  const card = document.createElement('div')
  card.className = 'card'
  card.innerHTML = `
    <div>
      <span class="code">${s.display_code}</span>
      ${badge(`${s.confidence} confidence`, s.confidence)}
      ${s.hcc_number ? badge(`HCC ${s.hcc_number}`, 'hcc') : ''}
      ${s.meat.map((m) => badge(m, 'meat')).join('')}
    </div>
    <p class="desc">${s.description}</p>
    ${s.evidence.map((q) => `<p class="quote">“${q.text}”</p>`).join('')}
    ${s.rationale ? `<p class="rationale">${s.rationale}</p>` : ''}
  `
  card.addEventListener('mouseenter', () => setActive(s.condition_id, true))
  card.addEventListener('mouseleave', () => setActive(s.condition_id, false))
  suggestionsEl.append(card)
}

// --- not coded ------------------------------------------------------------
for (const c of demo.conditions.filter((c) => c.status !== 'active')) {
  const li = document.createElement('li')
  const quote = c.quotes[0] ? ` — “${c.quotes[0].text}”` : ''
  li.innerHTML = `<strong>${c.label}</strong> ${badge(c.status.replaceAll('_', ' '), 'status')}${quote}`
  notCodedEl.append(li)
}

// --- audit verdicts -------------------------------------------------------
for (const f of demo.findings) {
  const row = document.createElement('tr')
  const evidence = f.evidence[0] ? `<div class="quote">“${f.evidence[0].text}”</div>` : ''
  row.innerHTML = `
    <td class="mono">${f.submitted_code ?? '—'}</td>
    <td>${badge(f.verdict.replaceAll('_', ' '), f.verdict)}</td>
    <td>${f.reason}${evidence}</td>
    <td class="mono">${f.suggested_code ?? '—'}</td>
  `
  findingsBody.append(row)
}
