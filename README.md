# ♠️ Blackjack Game Engine API

A production-grade full-stack Blackjack card game built with clean architecture, proper game logic separation, authentication, testing, and containerized deployment.

## 🏗 Architecture

```
Frontend (React)
    ⬇
Backend API (FastAPI)
    ⬇
PostgreSQL
```

## 🧱 Tech Stack

**Backend:**
- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- JWT Authentication
- Structured JSON logging

**Frontend:**
- React (Vite)
- Axios
- Clean UI

**Infrastructure:**
- Docker + Docker Compose (local development)
- Kubernetes on Minikube (home lab deployment)
- GitHub Actions CI (lint, test, security scan, publish)
- GitHub Container Registry (GHCR) — private image hosting
- Sealed Secrets (encrypted GHCR pull credentials in-repo)

## 🚀 Quick Start

### Local development (Docker Compose)

```bash
cp .env.example .env   # set a secure SECRET_KEY
make dev               # starts backend + frontend + postgres with hot-reload
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

### Home lab deployment (Minikube)

See [infra/README.md](infra/README.md) for the full guide. Short version:

```bash
# One-time cluster setup
minikube start --driver=docker --cpus=2 --memory=4g
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml
# Generate infra/k8s/ghcr-pull-secret.yaml with kubeseal — see infra/README.md

# Deploy
export DB_PASSWORD=yourpassword
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
./infra/k8s/deploy.sh

open http://$(minikube ip):30080
```

## 🎮 How to Play

1. **Register/Login** - Create an account or login
2. **Place Bet** - Enter your bet amount (starting balance: $1000)
3. **Play** - Click "Hit" to draw cards or "Stand" to hold
4. **Win** - Beat the dealer without going over 21!

## 📊 Game Rules

- Standard 52-card deck with automatic shuffle
- Dealer hits until 17
- Ace counts as 11 or 1
- Blackjack (natural 21) pays 3:2
- Regular win pays 1:1
- Push returns your bet

## 🧪 Running Tests

```bash
make test           # all tests
make test-coverage  # with coverage report

# Single test
docker compose run --rm -u root backend \
  sh -c "pip install -r requirements-dev.txt -q && pytest tests/test_game_engine.py::test_player_hit -v"
```

## 📚 API Endpoints

Routes are available at `/api/v1/{auth,game,stats}` (canonical) and `/{auth,game,stats}` (backward-compat).

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Game
- `POST /game/start` - Start new game
- `POST /game/hit` - Hit (draw card)
- `POST /game/stand` - Stand (dealer plays)
- `POST /game/split` - Split matching cards
- `GET /game/{game_id}` - Get game state

### Statistics
- `GET /stats` - Get player statistics

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check (includes DB connectivity)
- `GET /metrics` - Prometheus metrics

## 🗄 Database Schema

### Users Table
```sql
id: UUID (PK)
email: VARCHAR (UNIQUE)
password_hash: VARCHAR
balance: FLOAT
created_at: TIMESTAMP
```

### Games Table
```sql
id: UUID (PK)
user_id: UUID (FK)
status: VARCHAR (active/finished)
bet_amount: FLOAT
result: VARCHAR (win/lose/push/blackjack)
created_at: TIMESTAMP
```

### Game Cards Table
```sql
id: UUID (PK)
game_id: UUID (FK)
owner: VARCHAR (player/dealer)
card_rank: VARCHAR
card_suit: VARCHAR
order_index: INTEGER
```

## 🔐 Security

- Passwords hashed with bcrypt
- JWT-based authentication
- Protected endpoints require valid token
- No secrets in code (environment variables)

## 📝 Logging

Structured JSON logs include:
- User ID
- Game ID
- Bet amount
- Game result
- Request path
- Response time

View logs:
```bash
docker compose logs -f backend
```

## 🛠 Development

```bash
make dev       # start everything with hot-reload
make test      # run backend tests
make lint      # ruff + black check
make format    # auto-format with black
make migrate   # apply Alembic migrations
make migration # generate a new migration
make logs      # tail backend logs
```

See [CLAUDE.md](CLAUDE.md) for the full command reference.

## 🧹 Project Structure

```
blackjack/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routes/
│   │   ├── services/
│   │   │   ├── game_engine.py
│   │   │   └── deck.py
│   │   ├── core/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🎯 Core Features

✅ User registration and authentication
✅ JWT-based session management
✅ Full blackjack game logic (hit, stand, split, blackjack)
✅ Betting system with bankroll and daily bonus
✅ Win/lose/push detection
✅ Player statistics tracking
✅ Card deal animations
✅ Structured JSON logging + Prometheus metrics
✅ Comprehensive tests (unit, integration, E2E)
✅ Docker Compose (dev) + Minikube/Kubernetes (home lab)
✅ GitHub Actions CI — lint, test, Trivy scan, publish to GHCR
✅ Sealed Secrets for private registry auth
✅ Clean architecture (routes → services → models)

## 📖 API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

This is a portfolio/learning project. Feel free to fork and modify!

## 📄 License

MIT

## 👤 Author

Built as a DevOps portfolio project demonstrating:
- Clean architecture
- Testing practices
- Containerization
- Production best practices
