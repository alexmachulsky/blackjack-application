"""
Tests for app/routes/game.py (all endpoints + helpers).

Strategy
--------
* Use a real TestClient backed by SQLite — same as conftest.py.
* Inject controlled GameEngine instances directly into the module-level
  ``active_games`` dict so we can deterministically exercise every code branch
  without relying on a specific shuffled deck ordering.
* Clean up ``active_games`` after every test to prevent cross-test leakage.
"""

import pytest
from fastapi.testclient import TestClient

from app.routes.game import active_games
from app.services.game_engine import GameEngine
from app.services.deck import Card, Rank, Suit

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_USER = {"email": "gamer@example.com", "password": "GamePass123!"}
_BET = 50.0


def _make_headers(client: TestClient) -> dict:
    """Register + login and return Bearer auth headers."""
    client.post("/auth/register", json=_USER)
    resp = client.post("/auth/login", json=_USER)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _start_game(client: TestClient, headers: dict, bet: float = _BET) -> dict:
    """Start a game and return the parsed JSON response."""
    resp = client.post("/game/start", headers=headers, json={"bet_amount": bet})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_engine_with_hand(
    player_cards: list[Card],
    dealer_cards: list[Card],
) -> GameEngine:
    """
    Build a real GameEngine whose hands are pre-loaded with the given cards.
    The internal deck still exists (for dealing additional cards in hit / stand).
    """
    engine = GameEngine()
    engine.player_hands[0].cards = list(player_cards)
    engine.dealer_hand.cards = list(dealer_cards)
    return engine


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup_active_games():
    """Remove every engine registered during a test to prevent leakage."""
    yield
    active_games.clear()


# ──────────────────────────────────────────────────────────────────────────────
# POST /game/start
# ──────────────────────────────────────────────────────────────────────────────


def test_start_game_returns_game_state(client):
    headers = _make_headers(client)
    data = _start_game(client, headers)

    assert "game_id" in data
    assert data["bet_amount"] == _BET
    assert len(data["player_hand"]) == 2
    assert len(data["dealer_hand"]) == 1  # hole card hidden


def test_start_game_deducts_balance(client):
    headers = _make_headers(client)
    # First call: get initial balance from profile (stats endpoint)
    data = _start_game(client, headers)
    # new_balance should equal default_balance − bet
    assert data["new_balance"] == pytest.approx(1000.0 - _BET)


def test_start_game_invalid_bet_returns_400(client):
    headers = _make_headers(client)
    resp = client.post("/game/start", headers=headers, json={"bet_amount": 0})
    assert resp.status_code == 400
    assert "positive" in resp.json()["detail"].lower()


def test_start_game_negative_bet_returns_400(client):
    headers = _make_headers(client)
    resp = client.post("/game/start", headers=headers, json={"bet_amount": -10})
    assert resp.status_code == 400


def test_start_game_insufficient_balance_returns_400(client):
    headers = _make_headers(client)
    resp = client.post("/game/start", headers=headers, json={"bet_amount": 99999.0})
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()


def test_start_game_without_auth_returns_401(client):
    resp = client.post("/game/start", json={"bet_amount": _BET})
    assert resp.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# GET /game/{game_id}
# ──────────────────────────────────────────────────────────────────────────────


def test_get_game_active(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    resp = client.get(f"/game/{game_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["game_id"] == game_id


def test_get_game_finished(client):
    """Finish a game via stand, then GET should show all dealer cards."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] == "active":
        # Stand to finish the game (dealer auto-plays)
        stand = client.post("/game/stand", headers=headers, json={"game_id": game_id})
        assert stand.status_code == 200

    resp = client.get(f"/game/{game_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"


def test_get_game_not_found_returns_404(client):
    headers = _make_headers(client)
    import uuid

    resp = client.get(f"/game/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /game/hit
# ──────────────────────────────────────────────────────────────────────────────


def test_hit_game_not_found_returns_404(client):
    headers = _make_headers(client)
    import uuid

    resp = client.post(
        "/game/hit", headers=headers, json={"game_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


def test_hit_on_finished_game_returns_400(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] == "active":
        client.post("/game/stand", headers=headers, json={"game_id": game_id})

    resp = client.post("/game/hit", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 400


def test_hit_on_game_with_no_engine_returns_400(client):
    """Simulate a server restart: game exists in DB but engine was lost."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] == "active":
        # Remove the engine to simulate missing in-memory state
        active_games.pop(str(game_id), None)
        resp = client.post("/game/hit", headers=headers, json={"game_id": game_id})
        assert resp.status_code == 400
        assert "engine" in resp.json()["detail"].lower()


def test_hit_returns_game_state_or_finishes(client):
    """Hit should either return an active state (card added) or finish on bust."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before hit")

    # Inject a controlled engine with a safe hand (value 15) so hit doesn't bust
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.SEVEN, Suit.HEARTS), Card(Rank.EIGHT, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SIX, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/hit", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("active", "finished")


def test_hit_bust_resolves_game(client):
    """When the third card busts the player, the game must finish immediately."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before hit")

    # Hand value 20 — any card ≥ 2 busts (well, any non-ace 2-value card)
    # Force a near-bust hand: TEN + NINE = 19; next card from deck will push to 20+
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.TEN, Suit.HEARTS), Card(Rank.NINE, Suit.CLUBS)],
        dealer_cards=[Card(Rank.SEVEN, Suit.SPADES), Card(Rank.EIGHT, Suit.DIAMONDS)],
    )
    # deck.deal() uses list.pop() — append so the TEN is dealt next
    engine.deck.cards.append(Card(Rank.TEN, Suit.CLUBS))
    active_games[str(game_id)] = engine

    resp = client.post("/game/hit", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"


# ──────────────────────────────────────────────────────────────────────────────
# POST /game/stand
# ──────────────────────────────────────────────────────────────────────────────


def test_stand_game_not_found_returns_404(client):
    headers = _make_headers(client)
    import uuid

    resp = client.post(
        "/game/stand", headers=headers, json={"game_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


def test_stand_resolves_game(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before stand")

    resp = client.post("/game/stand", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "finished"
    assert data["result"] in ("win", "lose", "push", "blackjack")
    # After finish, dealer hand is fully revealed
    assert len(data["dealer_hand"]) >= 2


def test_stand_shows_full_dealer_hand(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before stand")

    # Inject deterministic engine: player 20, dealer 16 (will hit once)
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.TEN, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SIX, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/stand", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "finished"
    # Dealer had 16 → had to draw; so at least 2 cards exposed
    assert len(data["dealer_hand"]) >= 2


# ──────────────────────────────────────────────────────────────────────────────
# POST /game/double-down
# ──────────────────────────────────────────────────────────────────────────────


def test_double_down_success(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before double-down")

    # Inject engine with exactly 2 cards (always can_double_down)
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.FIVE, Suit.HEARTS), Card(Rank.SIX, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/double-down", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "finished"
    # Bet should have doubled
    assert data["bet_amount"] == pytest.approx(_BET * 2)


def test_double_down_not_available_returns_400(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before double-down")

    # Give player 3 cards → can_double_down() returns False
    engine = _make_engine_with_hand(
        player_cards=[
            Card(Rank.FIVE, Suit.HEARTS),
            Card(Rank.SIX, Suit.CLUBS),
            Card(Rank.TWO, Suit.DIAMONDS),
        ],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.HEARTS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/double-down", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 400
    assert "double down" in resp.json()["detail"].lower()


def test_double_down_insufficient_balance_returns_400(client):
    """User has no balance left to match the bet."""
    headers = _make_headers(client)
    # Bet the entire balance away
    start_resp = client.post(
        "/game/start", headers=headers, json={"bet_amount": 1000.0}
    )
    assert start_resp.status_code == 200
    game_id = start_resp.json()["game_id"]
    start_status = start_resp.json()["status"]

    if start_status != "active":
        pytest.skip("Initial deal resolved before double-down")

    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.FIVE, Suit.HEARTS), Card(Rank.SIX, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/double-down", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()


def test_double_down_game_not_found_returns_404(client):
    headers = _make_headers(client)
    import uuid

    resp = client.post(
        "/game/double-down", headers=headers, json={"game_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /game/split
# ──────────────────────────────────────────────────────────────────────────────


def test_split_success(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before split")

    # Two 8s → can_split() is True
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.EIGHT, Suit.HEARTS), Card(Rank.EIGHT, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/split", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    data = resp.json()
    # Either still active (more hands to play) or resolved
    assert data["status"] in ("active", "finished")
    assert data["is_split"] is True


def test_split_aces_auto_resolves(client):
    """Splitting aces should auto-complete immediately (no more player actions)."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before split")

    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/split", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "finished"


def test_split_cannot_split_returns_400(client):
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved before split")

    # Different ranks → can_split() is False
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.FIVE, Suit.HEARTS), Card(Rank.SIX, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/split", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 400
    assert "split" in resp.json()["detail"].lower()


def test_split_insufficient_balance_returns_400(client):
    headers = _make_headers(client)
    start_resp = client.post(
        "/game/start", headers=headers, json={"bet_amount": 1000.0}
    )
    assert start_resp.status_code == 200
    game_id = start_resp.json()["game_id"]
    start_status = start_resp.json()["status"]

    if start_status != "active":
        pytest.skip("Initial deal resolved before split")

    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.EIGHT, Suit.HEARTS), Card(Rank.EIGHT, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SEVEN, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    resp = client.post("/game/split", headers=headers, json={"game_id": game_id})
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()


def test_split_game_not_found_returns_404(client):
    headers = _make_headers(client)
    import uuid

    resp = client.post(
        "/game/split", headers=headers, json={"game_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Split hand continuation — hit on second hand after split
# ──────────────────────────────────────────────────────────────────────────────


def test_hit_on_split_hand_advances_or_finishes(client):
    """After a split, hitting on the active hand should work normally."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved")

    # Set up matching pair so split succeeds
    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.SEVEN, Suit.HEARTS), Card(Rank.SEVEN, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SIX, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    split_resp = client.post("/game/split", headers=headers, json={"game_id": game_id})
    assert split_resp.status_code == 200

    if split_resp.json()["status"] == "active":
        hit_resp = client.post("/game/hit", headers=headers, json={"game_id": game_id})
        assert hit_resp.status_code == 200
        assert hit_resp.json()["status"] in ("active", "finished")


def test_stand_on_split_advances_to_next_hand(client):
    """Standing on the first split hand should advance to the second hand."""
    headers = _make_headers(client)
    start = _start_game(client, headers)
    game_id = start["game_id"]

    if start["status"] != "active":
        pytest.skip("Initial deal resolved")

    engine = _make_engine_with_hand(
        player_cards=[Card(Rank.NINE, Suit.HEARTS), Card(Rank.NINE, Suit.CLUBS)],
        dealer_cards=[Card(Rank.TEN, Suit.SPADES), Card(Rank.SIX, Suit.DIAMONDS)],
    )
    active_games[str(game_id)] = engine

    split_resp = client.post("/game/split", headers=headers, json={"game_id": game_id})
    assert split_resp.status_code == 200

    if split_resp.json()["status"] == "active":
        # Stand on first hand — should move to hand index 1 or finish
        stand_resp = client.post(
            "/game/stand", headers=headers, json={"game_id": game_id}
        )
        assert stand_resp.status_code == 200
        assert stand_resp.json()["status"] in ("active", "finished")
