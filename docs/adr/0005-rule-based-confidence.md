# ADR 0005: Rule-based confidence levels

**Status:** accepted · **Date:** 2026-10-04

## Context

Each suggestion carries a confidence level (High / Medium / Low) that drives
the review UI: High can be bulk-accepted, Medium and Low land in "Needs
review". A statistical confidence model would need labeled outcomes Vero
does not have yet.

## Decision

Confidence comes from short, readable rules in
`vero_core/steps/finalize.py`, with every applied reason stored on the
suggestion (`confidence_reasons`):

- **High** — all of: every quote matched exactly and unambiguously; at least
  one MEAT element; candidate rank ≤ 3 (search rank, inherited by
  category-expanded codes); model certainty `high`; no flags (reconcile
  flags *and* model specificity flags).
- **Low** — any of: `no_meat`; `excludes1_conflict`; model certainty `low`;
  candidate rank ≥ 11.
- **Medium** — everything else, with the failed High criteria recorded as
  the reasons.

Thresholds (3 and 11) live in `PipelineConfig`, not as literals.

## Checking the rules against reality

Two feedback loops, built in later phases, keep the rules honest:

- The evaluation command reports accuracy per confidence level; High must be
  clearly more accurate than Low or the rules get revised.
- The dashboard tracks live acceptance rate by confidence.

## Consequences

- Any reviewer can read why a suggestion got its level.
- The levels are ordinal, not probabilities. Statistical calibration trained
  on reviewer decisions is on the roadmap once decision data exists.
