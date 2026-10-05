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

## Latest results — 2026-10-05, test split (8 notes, 4 audit cases)

Model `gemini-flash-lite-latest`, prompts extract v1 / select v1, reviewed
answer key (verification-pass review; see DATASET_CARD). Small split —
treat every number as directional.

| Metric | Score |
|---|---|
| Code-level P / R / F1 | 57% / 67% / **62%** |
| Category-level (partial credit) P / R | 67% / 78% |
| **HCC-level P / R** | 88% / **100%** |
| Hard cases correctly left uncoded | **11/11 (100%)** — all six patterns |
| Unverified quotes shown | **0** |
| Invalid/non-billable codes shown | **0** |
| Run success rate | 8/8 |
| Audit verdict accuracy | 70% (unsupported caught **6/6**; supported wrongly flagged 1/3) |

**The safety story held.** Every history-of, rule-out, negated,
family-history, resolved, and problem-list-only condition was correctly
left uncoded; zero fabricated evidence and zero invalid codes reached the
UI; and every HCC-relevant diagnosis was found (100% HCC recall) — the
numbers that matter for the compliance thesis are the strong ones.

**Accuracy by confidence is not yet calibrated**: High 57% ≈ Medium 54%,
Low 100% (n=2 inverts on a tiny sample). ADR 0005's check fails at this
scale; revisit the rules once more decisions exist.

### Error analysis — the five recurring mistakes

1. **Integral-symptom overcoding (most common).** The model added symptom
   codes that are integral to an already-coded condition: cough `R05.9`
   and sputum `R09.3` alongside COPD, fatigue `R53.83` alongside CKD-4.
   Guideline: don't code symptoms integral to a coded diagnosis. Fix:
   an explicit rule + example in `extract`/`select` v2 prompts.
2. **Hypertension handling is the weakest spot.** note_09's clearly
   treated hypertension produced *zero* codes (extraction or selection
   dropped it entirely), and note_06 missed the `I12.9` hypertensive-CKD
   presumption. The one audit miss ('supported wrongly flagged') was the
   direct cascade: coding missed HTN, so the audit judged submitted `I10`
   unsupported. Audit quality is bounded by coding quality.
3. **Specificity in both directions.** Under: `J44.9` chosen while the
   note documents an acute exacerbation (`J44.1`). Over: BMI 38 upgraded
   to morbid obesity `E66.01` when the provider documented no class
   (gold `E66.9`) — the exact overcoding pattern regulators flag.
4. **Tobacco confusion.** note_02's counseled tobacco use disorder was
   coded `Z72.0` (tobacco use) instead of `F17.210` (dependence), and the
   dependence code was dropped by post-validation elsewhere; candidate
   retrieval for behavioral/dependence phrasing needs work.
5. **Soft-MEAT misses.** note_10's GERD ("symptoms controlled, continue
   omeprazole" — clearly addressed) was never suggested: likely retrieval
   or extraction treating a short A/P line as not codeworthy.

Items 1–3 are prompt-rule candidates for `extract_v2`/`select_v2` (never
edit v1); item 4 may also need retrieval tuning. Rerunning after prompt
changes costs fresh API calls only for changed prompts — everything else
replays from cache.
