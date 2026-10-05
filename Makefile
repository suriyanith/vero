.PHONY: setup up down init test lint typecheck fmt gen-api eval live-smoke

BACKEND = cd backend && uv run
FRONTEND = cd frontend && npm

setup:
	cd backend && uv sync
	cd frontend && npm install
	uv tool install pre-commit 2>/dev/null || true
	pre-commit install || uv tool run pre-commit install
	@test -f .env || cp .env.example .env
	@echo "Done. Fill in GEMINI_API_KEY, GEMINI_MODEL, and seed passwords in .env"

up:
	docker compose up -d

down:
	docker compose down

init:
	$(BACKEND) python manage.py migrate
	@echo "TODO Phase 1: load_icd10cm, load_hcc_map"
	@echo "TODO Phase 3: seed_users, load_samples"

test:
	$(BACKEND) pytest
	$(FRONTEND) test -- --run

lint:
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(FRONTEND) run lint
	$(FRONTEND) run format:check

typecheck:
	$(BACKEND) mypy .
	$(FRONTEND) run typecheck

fmt:
	$(BACKEND) ruff check --fix .
	$(BACKEND) ruff format .
	$(FRONTEND) run format

gen-api:
	@echo "TODO Phase 4: openapi-typescript from /api/openapi.json"

eval:
	@echo "TODO Phase 7: manage.py run_eval --split test"

live-smoke:
	@echo "TODO Phase 2: run 3 sample notes against the real Gemini API"
