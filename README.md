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

Prerequisites: Docker (or local Python 3.12+/Node 22+/Postgres 16), a
[Google AI Studio](https://aistudio.google.com/) key — new accounts use
prepaid credits (load a small amount at ai.studio/projects; prepay acts as
a hard spending cap) — and the CMS reference files downloaded into `data/raw/` —
exact download/unzip commands are in [`data/SOURCES.md`](data/SOURCES.md).

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

Measured on the 12-note synthetic test split with `gemini-flash-lite-latest`
(small sample — directional; full method and error analysis in
[`docs/EVALUATION.md`](docs/EVALUATION.md)):

| Metric | Result |
|---|---|
| Hard cases correctly left uncoded (rule-out, history, negated, …) | **11/11** |
| HCC-level recall (payment-relevant diagnoses found) | **100%** |
| Unverified quotes / invalid codes shown to users | **0 / 0** |
| Audit mode: unsupported submitted codes caught | **6/6** |
| Code-level exact-match F1 | 62% |

The compliance-critical numbers are the strong ones by design; the exact-code
F1 reflects the free-tier model and the five error patterns are analyzed in
the doc. `manage.py run_eval` refuses unreviewed labels unless told
otherwise, and reruns replay from the response cache for free. Labeling
provenance and limits: [`docs/DATASET_CARD.md`](docs/DATASET_CARD.md).

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
