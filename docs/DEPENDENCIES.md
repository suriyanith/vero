# Runtime dependencies and why they exist

Every runtime dependency gets a row. Dev/test-only tools (ruff, mypy, pytest,
ESLint, …) are standard and not listed.

## Backend (Python)

| Package | Why |
|---|---|
| `django` | Web framework: auth, ORM, migrations, admin, background-tasks API |
| `django-ninja` | Typed API endpoints with Pydantic schemas and OpenAPI docs |
| `pydantic` | Schemas for the `vero_core` pipeline and API payloads |
| `psycopg[binary]` | PostgreSQL driver |
| `django-environ` | Parse settings from environment variables, fail fast |
| `django-tasks-db` | Database-backed backend + worker for Django 6's `django.tasks` API |
| `google-genai` | Official Gemini SDK: structured output from Pydantic response schemas |

## Frontend (npm)

| Package | Why |
|---|---|
| `react`, `react-dom` | UI |
| `react-router-dom` | Routing |
| `@tanstack/react-query` | Server-state caching and run-status polling |
| `tailwindcss` (+ `@tailwindcss/vite`) | Styling |
