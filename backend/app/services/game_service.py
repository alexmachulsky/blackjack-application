"""
Game service — business logic extracted from routes/game.py.

Handles all game orchestration (validation, engine management, card persistence,
result resolution) so that routes remain thin request → service → response layers.
"""

import logging
import uuid
from decimal import Decimal
from typing import Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.game import Game, GameCard
from app.models.user import User
from app.schemas.game import CardSchema, GameState, HandState
from app.services.game_engine import GameEngine, Hand
from app.services.deck import Card, Rank, Suit

logger = logging.getLogger(__name__)

# In-memory storage for active game engines (in production, use Redis)
active_games: Dict[str, GameEngine] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def get_active_game(
    game_id: str,
    user_id,
    db: Session,
) -> Tuple[Game, GameEngine]:
    """
    Fetch a game that belongs to the user, verify it is active,
    and return both the DB record and the in-memory engine.
    Raises HTTPException on any validation failure.
    """
    try:
        game_uuid = uuid.UUID(game_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    game = (
        db.query(Game)
        .filter(
            Game.id == game_uuid,
            Game.user_id == user_id,
        )
        .first()
    )

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    if game.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is not active",
        )

    engine = active_games.get(str(game.id))
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game engine not found",
        )

    return game, engine


def save_player_card(
    card,
    game_id,
    hand_index: int,
    order_index: int,
    db: Session,
):
    """Persist a single player card to game_cards table."""
    db.add(
        GameCard(
            game_id=game_id,
            owner="player",
            card_rank=card.rank.value,
            card_suit=card.suit.value,
            order_index=order_index,
            hand_index=hand_index,
        )
    )


def save_dealer_cards(game_id, engine: GameEngine, db: Session, initial_count: int):
    """Persist only the newly dealt dealer cards (those beyond initial_count)."""
    for idx, card in enumerate(
        engine.dealer_hand.cards[initial_count:], start=initial_count
    ):
        db.add(
            GameCard(
                game_id=game_id,
                owner="dealer",
                card_rank=card.rank.value,
                card_suit=card.suit.value,
                order_index=idx,
                hand_index=0,  # dealer always hand_index 0
            )
        )
    db.commit()


def hand_states(engine: GameEngine) -> List[HandState]:
    """Build HandState list from current engine state (for split games)."""
    state = engine.get_game_state()
    return [
        HandState(
            cards=[CardSchema(**c) for c in hs["cards"]],
            value=hs["value"],
            status=hs["status"],
            can_double_down=hs["can_double_down"],
        )
        for hs in state["player_hands"]
    ]


def build_active_state(game: Game, engine: GameEngine, user: User) -> GameState:
    """
    Build a GameState response for a game still in progress.
    Hides the dealer's hole card and computes all Phase 1/2 flags.
    """
    state = engine.get_game_state()

    return GameState(
        game_id=str(game.id),
        status="active",
        bet_amount=float(game.bet_amount),
        player_hand=[CardSchema(**c) for c in state["player_hand"]],
        player_value=state["player_value"],
        dealer_hand=[CardSchema(**state["dealer_hand"][0])],  # hide hole card
        dealer_value=0,
        result=None,
        payout=None,
        new_balance=float(user.balance),
        can_double_down=state["can_double_down"],
        is_split=engine.is_split,
        can_split=state["can_split"],
        player_hands=hand_states(engine) if engine.is_split else None,
        current_hand_index=state["current_hand_index"] if engine.is_split else None,
    )


def finish_game(
    game: Game,
    engine: GameEngine,
    user: User,
    db: Session,
) -> GameState:
    """
    Resolve a completed game:
    - Evaluate all hands via determine_winner()
    - Pay out using per-hand wagers (supports split + double-down correctly)
    - Update DB, remove from active_games
    """
    results = engine.determine_winner()  # List[Tuple[str, float]]
    if len(engine.hand_bets) == len(results):
        hand_bets = [Decimal(str(b)) for b in engine.hand_bets]
    elif len(results) == 1:
        hand_bets = [Decimal(str(game.bet_amount))]
    else:
        # Defensive fallback for mismatched in-memory state.
        per_hand = Decimal(str(game.bet_amount)) / Decimal(str(len(results)))
        hand_bets = [per_hand for _ in results]

    total_payout = sum(
        hand_bets[i] * Decimal(str(multiplier))
        for i, (_, multiplier) in enumerate(results)
    )
    result_strings = [r for r, _ in results]
    payout_list = [
        float(hand_bets[i] * Decimal(str(multiplier)))
        for i, (_, multiplier) in enumerate(results)
    ]

    user.balance += total_payout
    game.bet_amount = sum(hand_bets, Decimal("0"))

    # Primary result string: single value for normal games, comma-joined for split
    primary_result = (
        result_strings[0] if len(result_strings) == 1 else ",".join(result_strings)
    )

    game.status = "finished"
    game.result = primary_result
    if engine.is_split:
        game.is_split = True

    db.commit()
    db.refresh(user)

    # Log outcome
    log_record = logging.LogRecord(
        name="game",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Game finished",
        args=(),
        exc_info=None,
    )
    log_record.user_id = str(user.id)
    log_record.game_id = str(game.id)
    log_record.game_result = primary_result
    log_record.bet_amount = game.bet_amount
    logger.handle(log_record)

    active_games.pop(str(game.id), None)

    state = engine.get_game_state()
    return GameState(
        game_id=str(game.id),
        status="finished",
        bet_amount=float(game.bet_amount),
        player_hand=[CardSchema(**c) for c in state["player_hand"]],
        player_value=state["player_value"],
        dealer_hand=[CardSchema(**c) for c in state["dealer_hand"]],
        dealer_value=state["dealer_value"],
        result=primary_result,
        payout=float(total_payout),
        new_balance=float(user.balance),
        can_double_down=False,
        is_split=engine.is_split,
        can_split=False,
        player_hands=hand_states(engine) if engine.is_split else None,
        current_hand_index=None,
        results=result_strings if engine.is_split else None,
        payouts=payout_list if engine.is_split else None,
    )


def _log_game_event(msg: str, user_id, game_id, bet_amount=None):
    """Emit a structured game log record."""
    log_record = logging.LogRecord(
        name="game",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    log_record.user_id = str(user_id)
    log_record.game_id = str(game_id)
    if bet_amount is not None:
        log_record.bet_amount = bet_amount
    logger.handle(log_record)


# ---------------------------------------------------------------------------
# Service actions
# ---------------------------------------------------------------------------


def start_game(bet_amount: Decimal, user: User, db: Session) -> GameState:
    """Validate bet, create game, deal initial cards, and return state."""

    # Server-side min/max bet enforcement
    if bet_amount < Decimal(str(settings.MIN_BET)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum bet is ${settings.MIN_BET}",
        )
    if bet_amount > Decimal(str(settings.MAX_BET)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum bet is ${settings.MAX_BET}",
        )

    if bet_amount > user.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance",
        )

    user.balance -= bet_amount

    game = Game(
        user_id=user.id,
        bet_amount=bet_amount,
        status="active",
    )
    db.add(game)
    db.commit()
    db.refresh(game)

    engine = GameEngine()
    engine.deal_initial_cards()
    engine.hand_bets = [bet_amount]
    active_games[str(game.id)] = engine

    # Persist initial cards
    for idx, card in enumerate(engine.player_hand.cards):
        save_player_card(card, game.id, hand_index=0, order_index=idx, db=db)

    for idx, card in enumerate(engine.dealer_hand.cards):
        db.add(
            GameCard(
                game_id=game.id,
                owner="dealer",
                card_rank=card.rank.value,
                card_suit=card.suit.value,
                order_index=idx,
                hand_index=0,
            )
        )

    db.commit()

    _log_game_event("Game started", user.id, game.id, bet_amount=float(bet_amount))

    # Resolve naturals immediately on initial deal.
    if engine.player_hand.is_blackjack() or engine.dealer_hand.is_blackjack():
        return finish_game(game, engine, user, db)

    return build_active_state(game, engine, user)


def player_hit(game_id: str, user: User, db: Session) -> GameState:
    """Player hits — request another card on the current hand."""

    game, engine = get_active_game(game_id, user.id, db)

    card = engine.player_hit()

    # Count existing player cards for this hand to determine order_index
    existing_count = len(
        [
            c
            for c in game.cards
            if c.owner == "player" and c.hand_index == engine.current_hand_index
        ]
    )
    save_player_card(
        card,
        game.id,
        hand_index=engine.current_hand_index,
        order_index=existing_count,
        db=db,
    )
    db.commit()

    if engine.player_hand.is_bust():
        if engine.is_split:
            # Auto-advance past the busted hand
            stand_result = engine.player_stand()
            if stand_result == "next_hand":
                return build_active_state(game, engine, user)

            # All split hands resolved — check if dealer needs to play
            all_bust = all(h.is_bust() for h in engine.player_hands)
            if not all_bust:
                initial_dealer_cards = len(engine.dealer_hand.cards)
                engine.dealer_play()
                save_dealer_cards(game.id, engine, db, initial_dealer_cards)

            return finish_game(game, engine, user, db)
        else:
            # Single-hand bust — resolve immediately (no dealer play needed)
            return finish_game(game, engine, user, db)

    return build_active_state(game, engine, user)


def player_stand(game_id: str, user: User, db: Session) -> GameState:
    """Player stands — dealer plays (or advance to next split hand) and game resolves."""

    game, engine = get_active_game(game_id, user.id, db)

    stand_result = engine.player_stand()

    if stand_result == "next_hand":
        # Split game: more hands remain — return active state for next hand
        return build_active_state(game, engine, user)

    # Final stand: dealer must play
    initial_dealer_cards = len(engine.dealer_hand.cards)
    engine.dealer_play()
    save_dealer_cards(game.id, engine, db, initial_dealer_cards)

    return finish_game(game, engine, user, db)


def player_double_down(game_id: str, user: User, db: Session) -> GameState:
    """
    Player doubles down:
    - Requires exactly 2 cards on the current hand
    - Deducts an additional bet equal to the original
    - Deals exactly 1 card, then dealer auto-plays and game resolves
    """
    game, engine = get_active_game(game_id, user.id, db)

    if not engine.can_double_down():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Double down only available on initial hand",
        )

    if not engine.hand_bets:
        engine.hand_bets = [Decimal(str(game.bet_amount))]

    hand_idx = engine.current_hand_index
    if hand_idx >= len(engine.hand_bets):
        engine.hand_bets.extend(
            [Decimal(str(game.bet_amount))] * (hand_idx + 1 - len(engine.hand_bets))
        )

    additional_bet = Decimal(str(engine.hand_bets[hand_idx]))

    if user.balance < additional_bet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance to double down",
        )

    # Charge additional wager for the active hand, then update total wager.
    user.balance -= additional_bet
    engine.hand_bets[hand_idx] += additional_bet
    game.bet_amount = sum(engine.hand_bets, Decimal("0"))

    # Deal one card and let dealer auto-play (inside engine)
    initial_dealer_cards = len(engine.dealer_hand.cards)
    card = engine.player_double_down()

    # Persist the new player card
    existing_count = len(
        [
            c
            for c in game.cards
            if c.owner == "player" and c.hand_index == engine.current_hand_index
        ]
    )
    save_player_card(
        card,
        game.id,
        hand_index=engine.current_hand_index,
        order_index=existing_count,
        db=db,
    )

    # Persist any new dealer cards drawn during auto-play
    save_dealer_cards(game.id, engine, db, initial_dealer_cards)

    db.commit()

    return finish_game(game, engine, user, db)


def player_split(game_id: str, user: User, db: Session) -> GameState:
    """
    Player splits their hand:
    - Requires 2 cards of identical rank
    - Deducts an additional bet equal to the original (one bet per hand)
    - Creates two independent hands, each dealt one additional card
    - For split aces: each hand gets exactly one card and both auto-stand
    """
    game, engine = get_active_game(game_id, user.id, db)

    if not engine.can_split():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only split matching ranks",
        )

    hand0_bet = (
        Decimal(str(engine.hand_bets[0]))
        if engine.hand_bets
        else Decimal(str(game.bet_amount))
    )
    if user.balance < hand0_bet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance to split",
        )

    # Deduct additional bet for the second hand
    user.balance -= hand0_bet

    # Perform the split (engine updates player_hands in place)
    card1, card2 = engine.player_split()
    if not engine.hand_bets:
        engine.hand_bets = [hand0_bet]
    if len(engine.hand_bets) == 1:
        engine.hand_bets.append(engine.hand_bets[0])
    game.bet_amount = sum(engine.hand_bets, Decimal("0"))

    # Persist cards: after split, hand 0 has [original_card, card1]
    #                             hand 1 has [split_card, card2]
    # The original cards are already in DB; we only need to save the two new dealt cards.
    existing_h0 = len(
        [c for c in game.cards if c.owner == "player" and c.hand_index == 0]
    )
    save_player_card(card1, game.id, hand_index=0, order_index=existing_h0, db=db)

    existing_h1 = len(
        [c for c in game.cards if c.owner == "player" and c.hand_index == 1]
    )
    # Also persist the split card (the one moved to hand 1 from DB perspective)
    split_card = engine.player_hands[1].cards[0]  # original card moved to hand 1
    save_player_card(split_card, game.id, hand_index=1, order_index=existing_h1, db=db)
    save_player_card(card2, game.id, hand_index=1, order_index=existing_h1 + 1, db=db)

    db.commit()

    # Split aces: both hands auto-stand, dealer plays, game over
    if engine.split_aces:
        initial_dealer_cards = len(engine.dealer_hand.cards)
        engine.dealer_play()
        save_dealer_cards(game.id, engine, db, initial_dealer_cards)
        return finish_game(game, engine, user, db)

    return build_active_state(game, engine, user)


def get_game_by_id(game_id: str, user: User, db: Session) -> GameState:
    """Get game state by ID (reconstructed from DB)."""

    try:
        game_uuid = uuid.UUID(game_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    game = (
        db.query(Game)
        .filter(
            Game.id == game_uuid,
            Game.user_id == user.id,
        )
        .first()
    )

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    # Reconstruct hands from database
    player_cards = sorted(
        [c for c in game.cards if c.owner == "player"],
        key=lambda x: (x.hand_index, x.order_index),
    )
    dealer_cards = sorted(
        [c for c in game.cards if c.owner == "dealer"],
        key=lambda x: x.order_index,
    )

    # Use hand_index=0 cards for primary hand display
    primary_player_cards = [c for c in player_cards if c.hand_index == 0]
    player_hand = Hand()
    for pc in primary_player_cards:
        player_hand.add_card(Card(Rank(pc.card_rank), Suit(pc.card_suit)))

    dealer_hand = Hand()
    for dc in dealer_cards:
        dealer_hand.add_card(Card(Rank(dc.card_rank), Suit(dc.card_suit)))

    if game.status == "active":
        dealer_hand_display = [
            CardSchema(rank=dealer_cards[0].card_rank, suit=dealer_cards[0].card_suit)
        ]
        dealer_value = 0
    else:
        dealer_hand_display = [
            CardSchema(rank=c.card_rank, suit=c.card_suit) for c in dealer_cards
        ]
        dealer_value = dealer_hand.value()

    return GameState(
        game_id=str(game.id),
        status=game.status,
        bet_amount=float(game.bet_amount),
        player_hand=[
            CardSchema(rank=c.card_rank, suit=c.card_suit) for c in primary_player_cards
        ],
        player_value=player_hand.value(),
        dealer_hand=dealer_hand_display,
        dealer_value=dealer_value,
        result=game.result,
        payout=None,
        new_balance=float(user.balance),
        is_split=game.is_split,
    )
