# Changelog

All notable changes to Vero are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and versions follow SemVer.

## [Unreleased]

### Added

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
