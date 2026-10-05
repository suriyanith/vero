# Vero

Vero is an evidence-first medical coding assistant. It reads a clinical note,
suggests ICD-10-CM diagnosis codes, and for every code shows the exact sentence
in the note that supports it, the MEAT evidence present, the HCC the code maps
to, and a confidence level. An audit mode checks codes that were already
submitted and marks each one supported or not. A human makes every final
decision, and every decision is saved in an append-only audit trail.

> **Synthetic data only.** Vero runs locally and is built for synthetic notes.
> Never paste real patient data into it.

## Status

Under construction — see `CHANGELOG.md` for progress and `docs/ROADMAP.md`
for what is out of scope for v1.

## Quickstart

```bash
cp .env.example .env    # then add GEMINI_API_KEY, GEMINI_MODEL, seed passwords
docker compose up -d
make init               # migrate, load ICD-10 and HCC files, seed users, load samples
open http://localhost:5173
```

Running without Docker (local Python and Node, Postgres from the `db` service
only) is also supported; see the Makefile targets.

## Architecture

- **backend/** — Django 6 + Django Ninja API, Postgres, database-backed task queue
- **backend/vero_core/** — framework-free pipeline (Pydantic, no Django imports)
- **frontend/** — React + TypeScript + Vite + Tailwind
- **landing/** — static demo page (no backend)

## Why local-only

A public site that calls an AI API on every request exposes cost and quota to
anyone, and an open text box invites real patient data, which would mean HIPAA
obligations. The public demo is a static page with precomputed results.

## License

MIT — see `LICENSE`.
