# ADR 0002: Postgres full-text + trigram search instead of a vector database

**Status:** accepted · **Date:** 2026-10-04

## Context

The pipeline retrieves candidate ICD-10-CM codes for each extracted condition,
and the UI needs a code-search box. Embeddings + a vector store is the
fashionable choice; Vero deliberately avoids it for v1.

## Decision

Use PostgreSQL's built-in search on the code descriptions:

- `websearch_to_tsquery` full-text search over the long description
  (weight A) plus the tabular inclusion terms (weight B), via a stored
  `SearchVectorField` with a GIN index, built at load time.
- `pg_trgm` trigram similarity as a secondary signal and a fallback for typos
  and abbreviations, with its own GIN index.
- Combined score: `0.7 * normalized_text_rank + 0.3 * trigram_similarity`
  (constants in `apps/reference/services.py`, tuned on the dev split).

## Why

- Clinical condition labels ("type 2 diabetes with CKD") share vocabulary
  with code descriptions, so lexical search works well; verified on the full
  FY2027 set: "type 2 diabetes chronic kidney disease" ranks E11.22 first.
- One datastore: no embedding pipeline, no model/version drift, nothing else
  to run in Docker, trivially explainable in an interview.
- The selection step (AI call 2) tolerates imperfect retrieval because it
  sees the top-k candidates plus their category siblings.

## Consequences

- Purely semantic matches ("elevated blood sugar" → diabetes codes) can be
  missed. Mitigations: inclusion terms are indexed, and the extraction step
  produces clinical phrasing. If evaluation shows retrieval misses, the
  roadmap has pgvector + the ICD-10-CM alphabetic index as the upgrade path.
