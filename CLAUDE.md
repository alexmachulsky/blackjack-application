# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands use Docker Compose and run via the Makefile:

```bash
make dev              # Start all services (backend, frontend, postgres) with hot-reload
make stop             # Stop all services
make build            # Build Docker images
make test             # Run all backend tests (pytest -v)
make test-coverage    # Run tests with coverage report
make lint             # Run ruff check + black --check
make format           # Auto-format with black
make migrate          # Apply Alembic migrations
make logs             # Tail backend logs
make clean            # Remove containers, volumes, images
```

### Running a Single Test

Tests run inside the Docker container:

```bash
# Single test function
docker compose run --rm -u root backend \
  sh -c "pip install -r requirements-dev.txt -q && pytest tests/test_game_engine.py::test_player_hit -v"

# By marker
docker compose run --rm -u root backend \
  sh -c "pip install -r requirements-dev.txt -q && pytest -m unit -v"

# By keyword
docker compose run --rm -u root backend \
  sh -c "pip install -r requirements-dev.txt -q && pytest -k 'blackjack' -v"
```

Test markers (defined in `backend/pytest.ini`): `unit`, `integration`, `slow`

### Lint Without Docker

```bash
cd backend && ruff check . && black --check .
```

## Deployment (Minikube)

```bash
# Start Minikube (one-time)
minikube start --driver=docker --cpus=2 --memory=4g
minikube addons enable metrics-server

# Deploy
export DB_PASSWORD=yourpassword
export SECRET_KEY=your-32-char-secret-key
./infra/k8s/deploy.sh

# Access
open http://$(minikube ip):30080
```

Images are published to GHCR by CI: `ghcr.io/alexmachulsky/blackjack-application/backend:VERSION`

## Architecture

**Backend** (`backend/app/`): Routes → Services → Models layering
- `routes/` — Thin HTTP controllers; validate inputs, call services, return schemas
- `services/` — Business logic (`GameEngine`, `Deck`, `Hand`)
- `models/` — SQLAlchemy 2.0 ORM using `Mapped[]` declarative style
- `schemas/` — Pydantic v2 request/response models with `ConfigDict(from_attributes=True)`
- `core/` — Config (pydantic-settings), DB session factory, JWT/bcrypt auth

**Frontend** (`frontend/src/`): React 19 (JSX, no TypeScript)
- `context/AuthContext.jsx` — Auth state (token, user); persists JWT in localStorage
- `services/api.js` — Axios client; interceptors attach Bearer token and clear on 401
- `pages/GamePage.jsx` — Main game UI with split-hand support and animation state
- Styling: single `App.css` file, no CSS modules or Tailwind

**API proxying**: In dev, Vite (`vite.config.js`) proxies `/auth`, `/game`, `/stats`, `/health` to `http://backend:8000`. In production, Nginx (`nginx.conf`) does the same — backend is internal ClusterIP only.

## Key Gotchas

1. **In-memory game state**: `active_games: Dict[str, GameEngine]` in `backend/app/routes/game.py` is module-level and worker-local. Game state is lost on pod restart or with `--workers 2`. This is a known limitation; prod uses `--workers 2` in `docker-compose.prod.yml`.

2. **Split hand result encoding**: `Game.result` is stored as a comma-separated string (e.g., `"win,blackjack"`) to represent per-hand outcomes after a split. The stats endpoint parses this.

3. **Decimal/float boundary**: DB columns use `Numeric(10,2)` and business logic uses Python `Decimal`. Only convert to `float` at API serialization (schema layer). Never use `float` in payout calculations.

4. **Test DB isolation**: `backend/tests/conftest.py` uses SQLite in-memory with `StaticPool` (single shared connection). Game route tests use `app.dependency_overrides` to inject mock `GameEngine` instances — they don't exercise the in-memory state dict.

## Code Style

### Python (Backend)

Import order: stdlib → third-party → app-local, separated by blank lines.

Naming: `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants, `_prefix` for private helpers.

Type hints required on all function signatures. No `pyproject.toml` or config overrides — `black` and `ruff` run with defaults.

### JavaScript (Frontend)

No TypeScript. `camelCase` functions/variables, `PascalCase` components, `UPPER_CASE` constants. Functional components with hooks only.

## Environment Variables

Key variables (see `.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `SECRET_KEY` | — | JWT signing secret (min 32 chars, validated at startup) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token TTL |
| `INITIAL_BALANCE` | `1000.0` | Starting balance for new users |
| `CORS_ORIGINS` | — | Comma-separated allowed origins |
