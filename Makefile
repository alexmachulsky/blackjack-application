# ============================================================
# Developer convenience Makefile
# All targets assume Docker + Docker Compose are available.
# ============================================================

.PHONY: help dev stop build test lint format migrate shell clean

# Default target
help:
	@echo ""
	@echo "  make dev        Start all services (development)"
	@echo "  make stop       Stop all services"
	@echo "  make build      Build Docker images"
	@echo "  make test       Run backend unit tests"
	@echo "  make lint       Run ruff + black check on backend"
	@echo "  make format     Auto-format backend code with black"
	@echo "  make migrate    Run Alembic DB migrations"
	@echo "  make shell      Open a Python shell inside the backend container"
	@echo "  make clean      Remove containers, volumes, and dangling images"
	@echo ""

# ── Local development ──────────────────────────────────────────

dev:
	docker compose up --build

stop:
	docker compose down

build:
	docker compose build

# ── Testing ────────────────────────────────────────────────────

test:
	docker compose run --rm backend \
		sh -c "pip install -r requirements-dev.txt -q && pytest tests/ -v"

test-coverage:
	docker compose run --rm backend \
		sh -c "pip install -r requirements-dev.txt -q && \
		       pytest tests/ --cov=app --cov-report=term-missing"

# ── Linting & Formatting ───────────────────────────────────────

lint:
	docker compose run --rm backend \
		sh -c "pip install ruff black -q && ruff check . && black --check ."

format:
	docker compose run --rm backend \
		sh -c "pip install black -q && black ."

# ── Database ───────────────────────────────────────────────────

migrate:
	docker compose run --rm backend alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	docker compose run --rm backend alembic revision --autogenerate -m "$$msg"

# ── Utilities ──────────────────────────────────────────────────

shell:
	docker compose run --rm backend python

logs:
	docker compose logs -f backend

clean:
	docker compose down -v --remove-orphans
	docker image prune -f
