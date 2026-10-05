import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { EvidenceHighlighter } from './EvidenceHighlighter'
import { segment } from './highlight'

test('segment splits text at span boundaries', () => {
  //            0123456789
  const text = 'abcdefghij'
  const segments = segment(text.length, [
    { start: 2, end: 5, conditionId: 1 },
    { start: 7, end: 9, conditionId: 2 },
  ])
  expect(segments).toEqual([
    { start: 0, end: 2, conditionIds: [] },
    { start: 2, end: 5, conditionIds: [1] },
    { start: 5, end: 7, conditionIds: [] },
    { start: 7, end: 9, conditionIds: [2] },
    { start: 9, end: 10, conditionIds: [] },
  ])
})

test('overlapping spans split into sub-segments instead of being lost', () => {
  const segments = segment(10, [
    { start: 0, end: 6, conditionId: 1 },
    { start: 4, end: 8, conditionId: 2 },
  ])
  expect(segments).toEqual([
    { start: 0, end: 4, conditionIds: [1] },
    { start: 4, end: 6, conditionIds: [1, 2] },
    { start: 6, end: 8, conditionIds: [2] },
    { start: 8, end: 10, conditionIds: [] },
  ])
})

test('renders marks containing exactly the quoted text', () => {
  const text = 'CHF stable on furosemide, no edema today.'
  render(<EvidenceHighlighter text={text} spans={[{ start: 0, end: 24, conditionId: 42 }]} />)
  const mark = screen.getByText('CHF stable on furosemide')
  expect(mark.tagName).toBe('MARK')
  expect(mark).toHaveAttribute('data-condition-id', '42')
  // The rest of the note is still there, unhighlighted.
  expect(screen.getByText(/no edema today/)).toBeInTheDocument()
})
