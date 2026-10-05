import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import type { Finding } from '../api/types'
import { AuditFindingsTable } from './AuditFindingsTable'

const FINDINGS: Finding[] = [
  {
    id: 1,
    submitted_code: 'E11.9',
    verdict: 'SPECIFICITY_MISMATCH',
    reason_code: 'SPECIFICITY_MISMATCH',
    reason: 'The note supports E11.22 instead.',
    evidence: [
      {
        text: 'Type 2 diabetes with CKD stage 3a',
        start: 0,
        end: 33,
        meat: ['assess'],
        match_type: 'exact',
        ambiguous: false,
      },
    ],
    suggested_code: 'E11.22',
    latest_decision: null,
  },
  {
    id: 2,
    submitted_code: 'C18.9',
    verdict: 'NOT_SUPPORTED',
    reason_code: 'HISTORICAL',
    reason: 'colon cancer is documented as historical.',
    evidence: [],
    suggested_code: '',
    latest_decision: {
      action: 'accept',
      final_code: '',
      reason: '',
      reviewer_name: 'Demo Coder',
      created_at: '2026-10-05T12:00:00Z',
    },
  },
]

test('renders verdicts, reasons, evidence, and suggested codes', () => {
  render(
    <AuditFindingsTable
      title="Submitted codes"
      findings={FINDINGS}
      onAccept={vi.fn()}
      onReject={vi.fn()}
    />,
  )
  expect(screen.getByText('SPECIFICITY MISMATCH')).toBeInTheDocument()
  expect(screen.getByText('NOT SUPPORTED')).toBeInTheDocument()
  expect(screen.getByText('E11.22')).toBeInTheDocument()
  expect(screen.getByText(/Type 2 diabetes with CKD stage 3a/)).toBeInTheDocument()
})

test('undecided rows offer accept/reject; decided rows show the decision', async () => {
  const onAccept = vi.fn()
  render(
    <AuditFindingsTable
      title="Submitted codes"
      findings={FINDINGS}
      onAccept={onAccept}
      onReject={vi.fn()}
    />,
  )
  // The decided C18.9 row shows its decision instead of buttons.
  expect(screen.getByText('accepted')).toBeInTheDocument()
  expect(screen.getByText(/Demo Coder/)).toBeInTheDocument()

  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Accept' }))
  expect(onAccept).toHaveBeenCalledWith(FINDINGS[0])
})

test('renders nothing for an empty findings list', () => {
  const { container } = render(
    <AuditFindingsTable title="Missed HCCs" findings={[]} onAccept={vi.fn()} onReject={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})
