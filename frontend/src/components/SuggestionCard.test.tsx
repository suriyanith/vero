import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import type { Suggestion } from '../api/types'
import { SuggestionCard } from './SuggestionCard'

const SUGGESTION: Suggestion = {
  id: 1,
  condition_id: 10,
  display_code: 'E11.22',
  description: 'Type 2 diabetes mellitus with diabetic chronic kidney disease',
  hcc_number: 37,
  hcc_label: 'Diabetes with Chronic Complications',
  evidence: [
    {
      text: 'Type 2 diabetes with CKD stage 3a - continue metformin',
      start: 0,
      end: 54,
      meat: ['treat'],
      match_type: 'exact',
      ambiguous: false,
    },
  ],
  meat: ['assess', 'treat'],
  confidence: 'high',
  confidence_reasons: ['no flags'],
  rationale: 'Combination code applies.',
  flags: [],
  candidate_rank: 1,
  latest_decision: null,
}

function renderCard(overrides: Partial<Suggestion> = {}) {
  const handlers = { onAccept: vi.fn(), onReject: vi.fn(), onModify: vi.fn() }
  render(<SuggestionCard suggestion={{ ...SUGGESTION, ...overrides }} {...handlers} />)
  return handlers
}

test('shows code, confidence, HCC, MEAT, and evidence', () => {
  renderCard()
  expect(screen.getByText('E11.22')).toBeInTheDocument()
  expect(screen.getByText('high confidence')).toBeInTheDocument()
  expect(screen.getByText('HCC 37')).toBeInTheDocument()
  expect(screen.getByText('treat')).toBeInTheDocument()
  expect(screen.getByText(/continue metformin/)).toBeInTheDocument()
})

test('action buttons call their handlers', async () => {
  const user = userEvent.setup()
  const handlers = renderCard()
  await user.click(screen.getByRole('button', { name: 'Accept' }))
  await user.click(screen.getByRole('button', { name: 'Reject' }))
  await user.click(screen.getByRole('button', { name: 'Modify' }))
  expect(handlers.onAccept).toHaveBeenCalledOnce()
  expect(handlers.onReject).toHaveBeenCalledOnce()
  expect(handlers.onModify).toHaveBeenCalledOnce()
})

test('shows the latest decision with reviewer and modified code', () => {
  renderCard({
    latest_decision: {
      action: 'modify',
      final_code: 'E11.21',
      reason: 'nephropathy documented',
      reviewer_name: 'Demo Coder',
      created_at: '2026-10-05T12:00:00Z',
    },
  })
  expect(screen.getByText('modified')).toBeInTheDocument()
  expect(screen.getByText(/→ E11.21/)).toBeInTheDocument()
  expect(screen.getByText(/Demo Coder/)).toBeInTheDocument()
})

test('no-MEAT suggestion says so in text, not just color', () => {
  renderCard({ meat: [] })
  expect(screen.getByText('no MEAT')).toBeInTheDocument()
})
