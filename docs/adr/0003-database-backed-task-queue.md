# ADR 0003: Database-backed task queue via django-tasks-db

**Status:** accepted · **Date:** 2026-10-04

## Context

Vero processes notes in the background (Section 11 of the plan). The plan
calls for Django's built-in `django.tasks` API with a database-backed backend
and says to verify the current recommended package.

## Decision

Verified against PyPI (2026-10-04): Django 6.x ships the `django.tasks` API in
core, and the database backend lives in the separate **`django-tasks-db`**
package (0.13.0) by the same author as the `django-tasks` backport. The
backport package itself is only needed on Django < 6, so Vero does not install
it.

Configuration:

- `django_tasks_db` in `INSTALLED_APPS`
- `TASKS = {"default": {"BACKEND": "django_tasks_db.DatabaseBackend", "QUEUES": ["default"]}}`
- Worker: `manage.py db_worker` (its own service in Docker Compose)
- Tests: `django.tasks.backends.immediate.ImmediateBackend` so tasks run
  synchronously

## Consequences

- Jobs live in Postgres: no Redis or Celery, one fewer moving part, and the
  queue is visible with plain SQL.
- Throughput is bounded by polling the database — fine at Vero's scale
  (free-tier Gemini is the real bottleneck at ~10 requests/minute).
- Old task rows need pruning eventually (`prune_db_task_results`).
