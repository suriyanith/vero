# Evaluation

How Vero is scored, and the latest results.

## Running it

```bash
make eval                     # = manage.py run_eval --split test --mode both
```

Prerequisites: the answer key is loaded (`make init` runs `load_samples` +
`load_gold_drafts`) and **reviewed in the admin** (see
`docs/DATASET_CARD.md`). `run_eval` refuses unreviewed labels unless
`--allow-unreviewed` is passed, and then marks the EvalRun provisional.

Reruns are free: every AI call goes through the response cache, so an
evaluation over an unchanged split with unchanged prompts makes zero API
calls.

## Metrics

**Coding** — code-level precision/recall/F1 (exact match, per note);
HCC-level P/R (did Vero find the right HCCs?); category-level (first 3
characters) P/R reported separately as partial credit; hard-case accuracy
(share of `GoldNonCode` conditions correctly left uncoded, per pattern);
accuracy by confidence level (High must clearly beat Low or the rules in
ADR 0005 get revised); evidence integrity (quotes dropped by the verifier;
unverified quotes shown to users — **must be 0**; invalid or non-billable
codes shown — **must be 0**).

**Audit** — accuracy per verdict, a confusion matrix
(`expected->actual` counts), the share of unsupported codes caught, and the
share of supported codes wrongly flagged.

**Operational** — run success rate, average and slowest processing time,
average tokens per note.

Results are stored as `EvalRun` rows and shown on the admin-only
`/evaluation` page.

## Latest results

_No reviewed evaluation has been run yet._ The pipeline and metrics are
fully exercised by the automated test suite (a perfect canned pipeline
scores 100% across the board, which validates the scoring math), but a real
evaluation needs:

1. a `GEMINI_API_KEY` in `.env` with `VERO_LLM_MODE=live`, and
2. the answer key reviewed in the admin.

After the first real run, record here: the headline table (code F1, HCC
recall, hard-case accuracy by pattern, confidence-level accuracy, audit
verdict accuracy) and a short human-written error analysis covering the 5
most common mistakes and why they happen.
