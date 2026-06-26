# =============================================================================
# Retail Data Warehouse & Analytics Platform — Makefile
# =============================================================================

.DEFAULT_GOAL := help

# Derive the DATABASE_URL from .env values (if sourced) or fall back to defaults
DB_HOST   ?= localhost
DB_PORT   ?= 5432
DB_NAME   ?= retail_warehouse
DB_USER   ?= retail_user
DB_PASS   ?= retail_pass_2024
DATABASE_URL ?= postgresql://$(DB_USER):$(DB_PASS)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)

# =============================================================================
# Targets
# =============================================================================

.PHONY: help setup install test lint format etl api docker-up docker-down \
        generate-data init-db clean migrate

## help: Show this help message (auto-generated from comments)
help:
	@echo ""
	@echo "Retail Data Warehouse — Available Targets"
	@echo "=========================================="
	@grep -E '^## ' $(MAKEFILE_LIST) | \
		sed 's/^## //' | \
		awk -F': ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

## setup: Create virtualenv, install deps, copy .env, and initialise the DB
setup: install init-db
	@if [ ! -f .env ]; then cp .env.example .env && echo "✔ .env created from .env.example"; fi
	@echo "✔ Setup complete"

## install: Install Python dependencies via Poetry
install:
	poetry install --no-interaction
	@echo "✔ Dependencies installed"

## test: Run the full test suite with coverage
test:
	poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html:reports/coverage
	@echo "✔ Tests complete — coverage report at reports/coverage/index.html"

## lint: Run Black (check) and isort (check) for code-style violations
lint:
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/
	@echo "✔ Lint passed"

## format: Auto-format code with Black and isort
format:
	poetry run black src/ tests/
	poetry run isort src/ tests/
	@echo "✔ Code formatted"

## etl: Execute the full ETL pipeline
etl:
	poetry run python -m src.etl.run_pipeline
	@echo "✔ ETL pipeline finished"

## api: Start the FastAPI development server
api:
	poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
	@echo "✔ API server stopped"

## docker-up: Start all Docker Compose services in detached mode
docker-up:
	docker compose up -d --build
	@echo "✔ Services are up"

## docker-down: Stop and remove all Docker Compose services
docker-down:
	docker compose down -v
	@echo "✔ Services are down"

## generate-data: Generate synthetic retail CSV datasets
generate-data:
	poetry run python -m src.etl.generate_data
	@echo "✔ Synthetic data generated in data/"

## init-db: Create database schema via Alembic migrations
init-db:
	poetry run alembic upgrade head
	@echo "✔ Database initialised"

## clean: Remove build artifacts, caches, and coverage reports
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .eggs/ reports/ htmlcov/ .coverage .mypy_cache/ .ruff_cache/
	@echo "✔ Cleaned"

## migrate: Generate a new Alembic migration (usage: make migrate MSG="description")
migrate:
	poetry run alembic revision --autogenerate -m "$(MSG)"
	@echo "✔ Migration created"
