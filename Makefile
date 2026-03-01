# ============================================================
# Developer convenience Makefile
# All targets assume Docker + Docker Compose are available.
# Supports both 'docker compose' (V2 plugin) and 'docker-compose' (V1 standalone).
# ============================================================

# Auto-detect compose command
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

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
	$(COMPOSE) up --build

stop:
	$(COMPOSE) down

build:
	$(COMPOSE) build

# ── Testing ────────────────────────────────────────────────────

test:
	$(COMPOSE) run --rm -u root backend \
		sh -c "pip install -r requirements-dev.txt -q && pytest tests/ -v"

test-coverage:
	$(COMPOSE) run --rm -u root backend \
		sh -c "pip install -r requirements-dev.txt -q && \
		       pytest tests/ --cov=app --cov-report=term-missing"

# ── Linting & Formatting ───────────────────────────────────────

lint:
	$(COMPOSE) run --rm -u root backend \
		sh -c "pip install ruff black -q && ruff check . && black --check ."

format:
	$(COMPOSE) run --rm -u root backend \
		sh -c "pip install black -q && black ."

# ── Database ───────────────────────────────────────────────────

migrate:
	$(COMPOSE) run --rm backend alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	$(COMPOSE) run --rm backend alembic revision --autogenerate -m "$$msg"

# ── Utilities ──────────────────────────────────────────────────

shell:
	$(COMPOSE) run --rm backend python

logs:
	$(COMPOSE) logs -f backend

clean:
	$(COMPOSE) down -v --remove-orphans
	docker image prune -f
