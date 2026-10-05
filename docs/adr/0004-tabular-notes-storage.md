# ADR 0004: How tabular-list notes are stored

**Status:** accepted · **Date:** 2026-10-04

## Context

The ICD-10-CM tabular list attaches conventions to codes — Excludes1,
Excludes2, "code first", "use additional code", inclusion terms — and a note
written on a category (e.g. `E11`) applies to every code beneath it
(`E11.22`). The reconcile rules and the selection prompt need these notes per
billable code without walking the hierarchy at request time.

## Decision

1. **One JSON field per code** (`Icd10Code.notes`) holding
   `inclusion_terms`, `excludes1`, `excludes2`, `code_first`,
   `use_additional`, plus `<type>_codes` lists of the ICD-10 code patterns
   referenced in each note's text (`"…(N18.1-N18.6)"` → `["N18.1", "N18.6"]`,
   `"(E10.-)"` → `["E10"]`), extracted at load time so rules never re-parse
   prose.
2. **Copy inherited notes down at load time.** Excludes1/2, code-first, and
   use-additional notes from ancestor `<diag>` nodes are merged into each
   descendant's row. Lookups are then a single row read.
3. **Inclusion terms are not inherited.** They describe the code they are
   written on (they feed that code's search vector); copying them down would
   distort search ranking for child codes.
4. **Chapter- and section-level notes are not inherited.** They are broad
   (e.g. chapter-level Excludes covering whole code ranges) and copying them
   to tens of thousands of rows would make the Excludes1 reconcile rule fire
   on pairs a human coder would never flag. v1 scopes inheritance to `<diag>`
   ancestors, i.e. the category and subcategory levels.
5. **7th-character codes** (order file rows with no XML `<diag>` node, e.g.
   `S72.001A`) take the notes of their nearest ancestor that has one.

## Consequences

- Reconcile rules are simple dict lookups on one row.
- The notes JSON duplicates ancestor text across siblings (~47k of 98k codes
  carry notes; total table size stays small).
- A missed chapter-level Excludes1 conflict is possible; accepted for v1 and
  revisitable if evaluation surfaces real cases.
