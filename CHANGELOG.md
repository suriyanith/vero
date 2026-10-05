# Changelog

All notable changes to Vero are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and versions follow SemVer.

## [Unreleased]

### Added

- Phase 6: audit trail and dashboard — `/decisions` with filters (reviewer,
  action, code, dates, run), decisions CSV export, per-run CSV export with
  decision history; audit trail page; decision history panel on run detail;
  `apps/dashboard` metrics (every metric unit-tested against hand-computed
  values), `/dashboard/summary`, and the dashboard page with metric cards,
  a runs-per-day line chart, an acceptance-by-confidence bar chart, and the
  review backlog list.

- Phase 5: audit mode — `audit_note` reuses the coding result (no extra AI
  calls) and classifies each submitted code through the ordered verdict
  ladder (INVALID_CODE → SUPPORTED → WEAK_SUPPORT → SPECIFICITY_MISMATCH →
  NOT_SUPPORTED with the non-coded condition's status → NOT_DOCUMENTED),
  plus two-way MISSED_HCC findings for documented HCC conditions never
  submitted; `AuditFinding` model, finding decisions (append-only, with
  snapshots; accepting a mismatch endorses the suggested code), audit runs
  complete when every finding is decided; new-run page gets a mode toggle
  and submitted-code chips; run detail renders the verdict table and
  missed-HCC section with per-row decisions.
- Phase 4: coding UI and review — append-only `ReviewDecision` with evidence
  snapshots (save/delete raise, admin read-only), decision endpoints with
  billable-code validation on modify, "Accept all High", runs auto-complete
  when every suggestion is decided; React pages for login, new run (paste /
  sample / batch tabs), work queue (filters, polling, pagination), and run
  detail with offset-based evidence highlighting, suggestion cards grouped
  by confidence, keyboard shortcuts (j/k/a/r/m/?), reject-reason dialog,
  code-search modal, and optimistic decision updates; TypeScript API types
  generated from the OpenAPI schema with freshness checks in CI.
- Phase 3: notes and runs — Note/Batch/Run/Condition/Suggestion models, the
  PHI tripwire (rejects SSN/phone/email/MRN/DOB patterns, passes clinical
  numbers), `process_run` background task on the database queue (idempotent,
  enqueued on commit), `fail_stuck_runs`, session auth with CSRF on every
  endpoint (health/csrf/login excepted), rate-limited login, `seed_users`,
  `load_samples`, and the `/samples`, `/runs`, `/batches`,
  `/runs/{id}`, `/runs/{id}/retry` endpoints with pagination and filters.
- Phase 2: framework-free `vero_core` pipeline — text normalization with
  offset mapping (property-tested), quote verification that drops anything
  not verbatim in the note, candidate retrieval with category expansion,
  batched code selection restricted to retrieved candidates, and a finalize
  step with reconcile rules (Excludes1, missing additional code,
  underspecified, no MEAT) and rule-based confidence (ADR 0005). Versioned
  prompts (`extract_v1`, `select_v1`), `FakeLLMClient`/`FakeCodeRepository`,
  a fixture-driven CLI, and `GeminiClient` with structured output, retries,
  client-side rate limiting, response caching, and usage logging
  (`LlmCall`/`LlmCache`). `make live-smoke` runs three bundled sample notes
  against the real API.
- Phase 1: ICD-10-CM FY2027 reference data (98,403 codes, 74,879 billable)
  with structured tabular notes copied down to billable codes (ADR 0004);
  CMS-HCC V28 PY2027 mapping (115 categories, 8,299 code mappings);
  idempotent, transactional, versioned loader commands; Postgres full-text +
  trigram code search (ADR 0002); `/api/codes/search` and
  `/api/codes/{code}` endpoints; read-only reference admin; `/api/health` now
  requires an active code set.
- Phase 0: repository skeleton, Django project with split settings and custom
  User model, Ninja API with `/api/health`, React + TypeScript + Vite +
  Tailwind frontend with dev proxy, Docker Compose, Makefile, pre-commit
  hooks, CI workflow, Dependabot, PR template, ADR 0001.
