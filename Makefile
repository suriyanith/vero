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

# Raw CMS files (see data/SOURCES.md for URLs and checksums)
ICD10_ORDER = ../data/raw/Code Descriptions/icd10cm_order_2027.txt
ICD10_XML   = ../data/raw/Table and Index/icd10cm_tabular_2027.xml
HCC_CSV     = ../data/raw/2027 Initial ICD-10-CM Mappings.csv
HCC_LABELS  = ../data/raw/model-software/V28/V28115L3.TXT

init:
	$(BACKEND) python manage.py migrate
	$(BACKEND) python manage.py load_icd10cm --fy 2027 --order-file "$(ICD10_ORDER)" --tabular-xml "$(ICD10_XML)"
	$(BACKEND) python manage.py load_hcc_map --model V28 --payment-year 2027 --file "$(HCC_CSV)" --labels-file "$(HCC_LABELS)"
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
	$(BACKEND) python manage.py code_note_file \
		../data/samples/note_01_diabetes_ckd.txt \
		../data/samples/note_02_chf_copd.txt \
		../data/samples/note_03_depression_obesity.txt
