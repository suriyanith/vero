# Vero synthetic dataset card

## What this dataset is

Synthetic outpatient SOAP notes for developing and evaluating Vero. Every
note is fictional, written for this project, and contains **no real patient
data** — no names, dates of birth, addresses, phone numbers, or record
numbers ("the patient" throughout; ages allowed).

## Provenance

- `note_01`–`note_12` were **hand-written** for this project
  (`data/samples/*.txt`), covering the scenario matrix below. `note_01` is
  the plan's Appendix C worked example.
- `manage.py generate_samples` can draft additional notes with Gemini
  (requires `GEMINI_API_KEY` and `VERO_LLM_MODE=live`); drafts append to
  `data/samples/manifest.json` with `split: none` until reviewed.
- The answer key (gold labels, do-not-code conditions, audit cases) lives in
  `data/samples/manifest.json` and loads via `manage.py load_gold_drafts`
  with **`reviewed=false`**.

## Review status — read this before trusting any number

**Draft labels are never treated as correct until a person reviews them.**
`run_eval` refuses to run on unreviewed labels unless `--allow-unreviewed`
is passed, and then marks the results provisional. Review happens in the
Django admin (Notes → inlines → "Mark reviewed" action).

The current labels were drafted by a non-certified coder following the
FY2027 ICD-10-CM Official Guidelines (outpatient sections) and verified
against the loaded FY2027 code set for existence and billability. They are
**drafts**: a certified coder (or at minimum a careful human pass against
the guidelines) must confirm every code and non-code before the evaluation
is quotable.

## Scenario matrix

Conditions (Medicare Advantage focus): type 2 diabetes ± complications, CKD
stages 3–4 and unspecified, chronic systolic CHF, COPD ± exacerbation,
atrial fibrillation, MDD recurrent, obesity/morbid obesity, OSA, PVD,
nicotine dependence, plus non-HCC conditions (hypertension, hyperlipidemia,
GERD).

Patterns: `WELL_DOCUMENTED`, `HISTORY_ONLY`, `RESOLVED`, `RULE_OUT`,
`NEGATED`, `FAMILY_HISTORY`, `PROBLEM_LIST_ONLY`, `VAGUE`, `PRESUMED_LINK`,
`MESSY`. Each note's tags are in the manifest.

## Splits

Fixed in the manifest: 4 notes `dev` (prompt tuning), 8 notes `test`
(untouched until evaluation). All notes are also available as samples in
the UI.

## Labeling rules applied

- Outpatient guidelines: no uncertain diagnoses ("rule out", "possible"),
  no resolved/history-of conditions, no negated conditions, no family
  history as patient diagnosis.
- The "with" convention: diabetes + CKD in the same note presumes linkage
  (`E11.22` + stage code) unless documented unrelated.
- Code to the highest documented specificity; `VAGUE` notes deliberately
  earn unspecified codes.
- `PROBLEM_LIST_ONLY` conditions get a `GoldNonCode` with reason `no_meat`.
- Tricky calls are explained in each label's `rationale` field.

## Known limits

- Small (12 notes); metrics have wide error bars and are directional only.
- The hard-case metric links a `GoldNonCode` to a suggestion by label
  substring containment (either direction, case-insensitive) — a crude but
  transparent heuristic, documented in `apps/evaluation/metrics.py`.
- Written by one author; style diversity is limited until generated notes
  are added and reviewed.
