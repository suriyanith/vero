# Vero

**An evidence-first medical coding assistant.** Vero reads a clinical note,
suggests ICD-10-CM diagnosis codes, and for every code shows the exact
sentence in the note that supports it, the MEAT evidence present, the
CMS-HCC (V28) category it maps to, and a readable confidence level. A second
mode audits codes that were already submitted and marks each one supported
or not. A human makes every final decision, and every decision is saved in
an append-only audit trail.

> **Synthetic data only.** Vero runs locally and is built for synthetic
> notes. A PHI tripwire rejects anything that looks like real patient
> identifiers — but it is a guardrail, not a de-identification tool. Never
> paste real patient data into Vero.

## Why

Under-coding loses providers revenue; over-coding creates compliance risk —
CMS RADV audits claw back payments for diagnoses the chart doesn't support,
and regulators have flagged AI tools that push coders to *add* diagnoses.
Vero's stance: every code traceable to verified evidence, reviewed by an
accountable human, recorded so it can be defended later — in both
directions (codes to add *and* codes to remove).

## How it works

```
note ──> 1 extract (AI)      conditions + verbatim quotes + status + MEAT tags
     ──> 2 verify (Python)   every quote checked against the note; fakes dropped
     ──> 3 retrieve (SQL)    candidates from the real FY2027 code set (FTS + trigram)
     ──> 4 select (AI)       codes chosen ONLY from the candidates; rest discarded
     ──> 5 finalize (Python) billable-check, Excludes1/`use additional` rules,
                             HCC V28 mapping, rule-based confidence
     ──> human review        accept / reject / modify; append-only decisions
```

Exactly **two AI calls per note**; everything that must be guaranteed is
deterministic Python. Audit mode reuses the coding result (no extra calls)
and classifies each submitted code: `SUPPORTED`, `WEAK_SUPPORT`,
`SPECIFICITY_MISMATCH` (with the better code), `NOT_SUPPORTED` (with the
reason — rule-out, history, negated…), or `INVALID_CODE`, plus `MISSED_HCC`
findings for documented HCC conditions never submitted.

### Hard guarantees (enforced by code and tests)

- **0 unverified quotes shown to users** — offsets are property-tested to
  slice the original note exactly.
- **0 invalid or non-billable codes shown** — the AI picks from retrieved
  real codes; results are validated against the CMS file.
- **Every review decision is permanent and attributable** — append-only
  rows with an evidence snapshot of what the reviewer saw.

## Quickstart

Prerequisites: Docker (or local Python 3.12+/Node 22+/Postgres 16), a free
[Google AI Studio](https://aistudio.google.com/) key (do **not** enable
billing on its project), and the CMS reference files (URLs + checksums in
`data/SOURCES.md`) downloaded into `data/raw/`.

```bash
cp .env.example .env     # add GEMINI_API_KEY, GEMINI_MODEL, seed passwords
docker compose up -d     # db + backend + worker + frontend
make init                # migrate, load ICD-10 + HCC data, seed users, load samples
open http://localhost:5173
```

Log in as `coder` (or `admin`) with the password you set in `.env`. Without
Docker: start Postgres, then `make setup`, `make init`, and run
`manage.py runserver`, `manage.py db_worker`, and `npm run dev` yourself.

Useful targets: `make test`, `make lint`, `make typecheck`, `make gen-api`
(regenerate TypeScript API types), `make live-smoke` (3 sample notes
against the real Gemini API), `make eval` (evaluation on the test split).

## What's inside

| Path | What |
|---|---|
| `backend/vero_core/` | Framework-free pipeline: Pydantic schemas, text/offset engine, 5 steps, prompts, fake + real LLM clients. Never imports Django (test-enforced). |
| `backend/apps/` | Django 6: reference data + search, runs + DB-backed task queue, review, dashboard, evaluation, LLM caching/usage |
| `frontend/` | React + TypeScript (strict) + Vite + Tailwind; API types generated from the OpenAPI schema |
| `landing/` | Static demo page replaying a precomputed run — no backend |
| `data/` | CMS source manifest, synthetic notes + answer-key manifest, test fixtures |
| `docs/` | ADRs 0001–0005, dataset card, evaluation doc, roadmap |

## Evaluation

`manage.py run_eval` scores the pipeline against a human-reviewed answer
key: code/HCC/category precision-recall-F1, hard-case accuracy (history,
rule-out, negated, family-history, problem-list-only…), accuracy by
confidence level, evidence-integrity counters, and audit verdict accuracy.
It refuses unreviewed labels unless told otherwise, and reruns are free via
the response cache. See `docs/EVALUATION.md` and `docs/DATASET_CARD.md` —
the bundled labels are **drafts pending human review**.

## Why local-only

A public site that calls an AI API on every request exposes quota and cost
to anyone; an open text box invites real patient notes, which would mean
HIPAA obligations (a BAA-covered AI service, encryption, access controls).
Out of scope by design — the public demo (`landing/`) is a static page with
precomputed results and no input.

## Limitations

Synthetic data only; the answer key was drafted by a non-certified coder
following the official guidelines and must be reviewed before quoting
results; outpatient ICD-10-CM only (no CPT/E/M — AMA-licensed — no
inpatient, no RAF calculation); confidence levels are rule-based, not
statistically calibrated; the free Gemini tier caps throughput (~10
requests/min — the worker paces itself).

Roadmap: `docs/ROADMAP.md`.

## License

MIT — see `LICENSE`.
