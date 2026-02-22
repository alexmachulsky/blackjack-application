"""
test_integration.py

Integration tests — validate HTTP API contracts via TestClient + SQLite.

These tests exercise the full request-response cycle including:
  - HTTP routing and middleware
  - FastAPI dependency injection
  - SQLAlchemy ORM with SQLite
  - JWT authentication flow

Marked with pytest.mark.integration so CI can run them in a dedicated
stage (Stage 5) — after unit tests and static analysis both pass.
"""

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Stage 5-A: Health check — zero auth required
# ---------------------------------------------------------------------------


def test_health_check_returns_200(client):
    """GET /health must return 200 and report healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "blackjack-api"
    assert "version" in body


# ---------------------------------------------------------------------------
# Stage 5-B: Auth — registration + login contract
# ---------------------------------------------------------------------------


def test_register_creates_user_with_default_balance(client):
    """POST /auth/register creates a user with initial balance."""
    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert body["balance"] == 1000.0
    assert "id" in body


def test_register_duplicate_email_returns_400(client):
    """POST /auth/register with a taken email must return 400."""
    payload = {"email": "dup@example.com", "password": "SecurePass123!"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_valid_credentials_returns_jwt(client):
    """POST /auth/login with correct credentials returns a Bearer token."""
    client.post(
        "/auth/register",
        json={"email": "validlogin@example.com", "password": "SecurePass123!"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "validlogin@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    # Token string must be non-trivial
    assert len(body["access_token"]) > 20


def test_login_wrong_password_returns_401(client):
    """POST /auth/login with incorrect password must return 401."""
    client.post(
        "/auth/register",
        json={"email": "wrongpass@example.com", "password": "CorrectPass123!"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "wrongpass@example.com", "password": "WrongPass!"},
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    """POST /auth/login for non-existent user must return 401."""
    response = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "Whatever123!"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Stage 5-C: Protected routes — must reject unauthenticated requests
# ---------------------------------------------------------------------------


def test_stats_without_auth_returns_403(client):
    """GET /stats without token must return 403 (FastAPI OAuth2 default)."""
    response = client.get("/stats")
    assert response.status_code == 403


def test_game_start_without_auth_returns_403(client):
    """POST /game/start without token must return 403 (FastAPI OAuth2 default)."""
    response = client.post("/game/start", json={"bet_amount": 50.0})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Stage 5-D: Full auth flow — register → login → play a hand
# ---------------------------------------------------------------------------


def _register_and_login(client, email: str = "player@example.com") -> dict:
    """Helper: register a user and return auth headers."""
    client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_game_start_with_valid_auth(client):
    """POST /game/start with a valid token must return a full game state."""
    headers = _register_and_login(client, "gamestart@example.com")
    response = client.post(
        "/game/start",
        json={"bet_amount": 50.0},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "game_id" in body
    assert body["status"] == "active"
    assert body["bet_amount"] == 50.0
    # Initial deal: player gets 2 cards; dealer shows only 1 (hole card hidden)
    assert len(body["player_hand"]) == 2
    assert len(body["dealer_hand"]) == 1


def test_game_start_invalid_bet_returns_error(client):
    """POST /game/start with a negative bet must be rejected."""
    headers = _register_and_login(client, "badbet@example.com")
    response = client.post(
        "/game/start",
        json={"bet_amount": -100.0},
        headers=headers,
    )
    assert response.status_code in (400, 422)


def test_stats_after_game(client):
    """GET /stats after starting a game must return valid stats for the user."""
    headers = _register_and_login(client, "stats@example.com")
    # Start a game to generate some stats activity
    client.post("/game/start", json={"bet_amount": 10.0}, headers=headers)
    response = client.get("/stats", headers=headers)
    assert response.status_code == 200
    body = response.json()
    # Stats must at least contain these fields
    assert "total_games" in body
    assert "current_balance" in body
