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
- Docker
- Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. **Clone the repository**
```bash
cd blackjack-app
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env and set a secure SECRET_KEY
```

3. **Build and run with Docker Compose**
```bash
docker compose up --build
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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
# Enter backend container
docker compose exec backend bash

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_game_engine.py -v
```

## 📚 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Game
- `POST /game/start` - Start new game
- `POST /game/hit` - Hit (draw card)
- `POST /game/stand` - Stand (dealer plays)
- `GET /game/{game_id}` - Get game state

### Statistics
- `GET /stats` - Get player statistics

### Health
- `GET /health` - Health check endpoint

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

### Backend Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run locally (requires PostgreSQL)
uvicorn app.main:app --reload
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Run dev server
npm run dev
```

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
✅ Full blackjack game logic  
✅ Betting system with bankroll  
✅ Win/lose/push detection  
✅ Player statistics tracking  
✅ Structured logging  
✅ Comprehensive tests  
✅ Docker containerization  
✅ Clean architecture  

## 🚧 Future Phases

- Phase 2: CI/CD pipeline, image scanning, registry
- Phase 3: Cloud deployment, Kubernetes, monitoring

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
