# ADR 0001: Django + Django Ninja backend, React + TypeScript frontend

**Status:** accepted · **Date:** 2026-10-04

## Context

Vero needs auth, a relational data model with migrations, an admin UI for
labeling gold data, a background job system, a typed JSON API, and an
interactive review UI. It is a portfolio project: every choice must be
explainable and boring in the good sense.

## Decision

- **Django 6.x** for the backend: batteries-included auth, ORM, migrations,
  admin (used for answer-key labeling), and the built-in `django.tasks`
  background tasks API, which removes the need for Redis/Celery.
- **Django Ninja** for the API: endpoints are plain typed functions using
  Pydantic — the same modeling library as the `vero_core` pipeline — and it
  generates an OpenAPI schema we use to produce TypeScript types.
- **PostgreSQL 16+**: production-grade, and its full-text search plus
  `pg_trgm` cover ICD-10 code retrieval without a vector database (see ADR
  0002 when written).
- **React + TypeScript (strict) + Vite** frontend with TanStack Query and
  Tailwind: the standard modern stack, with the Vite dev server proxying
  `/api` and `/admin` to Django so the browser sees one origin (session
  cookies and CSRF work with no CORS config).
- **`vero_core` stays framework-free**: it never imports Django, takes plain
  inputs, and returns Pydantic models. Django implements its interfaces
  (`CodeRepository`, `LLMClient`). A test enforces the import boundary.

## Consequences

- One language (Python) covers web, pipeline, and data loading.
- The admin gives a labeling UI for free.
- Two codebases (Python + TS) need two toolchains, mitigated by the Makefile
  and Docker Compose.
- If a required dependency does not support Django 6, the fallback is Django
  5.2 LTS with the `django-tasks` backport, recorded in a follow-up ADR.
