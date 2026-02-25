import logging
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.game import Game, GameCard
from app.schemas.game import GameStart, GameState, GameAction, CardSchema, HandState
from app.services.game_engine import GameEngine
from app.services.deck import Rank, Suit

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory storage for active game engines (in production, use Redis)
active_games: Dict[str, GameEngine] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_active_game(
    game_id: str,
    user_id,
    db: Session,
) -> tuple[Game, GameEngine]:
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


def _save_player_card(
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


def _save_dealer_cards(game_id, engine: GameEngine, db: Session, initial_count: int):
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


def _hand_states(engine: GameEngine) -> List[HandState]:
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


def _build_active_state(game: Game, engine: GameEngine, user: User) -> GameState:
    """
    Build a GameState response for a game still in progress.
    Hides the dealer's hole card and computes all Phase 1/2 flags.
    """
    state = engine.get_game_state()

    return GameState(
        game_id=str(game.id),
        status="active",
        bet_amount=game.bet_amount,
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
        player_hands=_hand_states(engine) if engine.is_split else None,
        current_hand_index=state["current_hand_index"] if engine.is_split else None,
    )


def _finish_game(
    game: Game,
    engine: GameEngine,
    user: User,
    db: Session,
) -> GameState:
    """
    Resolve a completed game:
    - Evaluate all hands via determine_winner()
    - Pay out: each hand is valued at game.bet_amount (original bet per hand)
    - Update DB, remove from active_games
    """
    results = engine.determine_winner()  # List[Tuple[str, float]]

    # Each hand (split or not) is worth the original per-hand bet stored in game.bet_amount.
    # For double-down the bet was already doubled in the DB before this helper is called,
    # so the multiplied amount flows through naturally.
    bet = Decimal(str(game.bet_amount))
    total_payout = sum(bet * Decimal(str(multiplier)) for _, multiplier in results)
    result_strings = [r for r, _ in results]
    payout_list = [float(bet * Decimal(str(m))) for _, m in results]

    user.balance += total_payout

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
        bet_amount=game.bet_amount,
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
        player_hands=_hand_states(engine) if engine.is_split else None,
        current_hand_index=None,
        results=result_strings if engine.is_split else None,
        payouts=payout_list if engine.is_split else None,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/start", response_model=GameState)
def start_game(
    game_data: GameStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new blackjack game."""

    if game_data.bet_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet amount must be positive",
        )

    if game_data.bet_amount > current_user.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance",
        )

    current_user.balance -= Decimal(str(game_data.bet_amount))

    game = Game(
        user_id=current_user.id,
        bet_amount=Decimal(str(game_data.bet_amount)),
        status="active",
    )
    db.add(game)
    db.commit()
    db.refresh(game)

    engine = GameEngine()
    engine.deal_initial_cards()
    active_games[str(game.id)] = engine

    # Persist initial cards
    for idx, card in enumerate(engine.player_hand.cards):
        _save_player_card(card, game.id, hand_index=0, order_index=idx, db=db)

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

    # Log start
    log_record = logging.LogRecord(
        name="game",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Game started",
        args=(),
        exc_info=None,
    )
    log_record.user_id = str(current_user.id)
    log_record.game_id = str(game.id)
    log_record.bet_amount = game_data.bet_amount
    logger.handle(log_record)

    state = engine.get_game_state()
    return GameState(
        game_id=str(game.id),
        status="active",
        bet_amount=game_data.bet_amount,
        player_hand=[CardSchema(**c) for c in state["player_hand"]],
        player_value=state["player_value"],
        dealer_hand=[CardSchema(**state["dealer_hand"][0])],  # show one dealer card
        dealer_value=0,
        result=None,
        payout=None,
        new_balance=float(current_user.balance),
        # Phase 1: True if pair was dealt (player can split or double)
        can_double_down=engine.can_double_down(),
        can_split=state["can_split"],
        is_split=False,
    )


@router.post("/hit", response_model=GameState)
def hit(
    action: GameAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Player hits — request another card on the current hand."""

    game, engine = _get_active_game(action.game_id, current_user.id, db)

    card = engine.player_hit()

    # Count existing player cards for this hand to determine order_index
    existing_count = len(
        [
            c
            for c in game.cards
            if c.owner == "player" and c.hand_index == engine.current_hand_index
        ]
    )
    _save_player_card(
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
                return _build_active_state(game, engine, current_user)

            # All split hands resolved — check if dealer needs to play
            all_bust = all(h.is_bust() for h in engine.player_hands)
            if not all_bust:
                initial_dealer_cards = len(engine.dealer_hand.cards)
                engine.dealer_play()
                _save_dealer_cards(game.id, engine, db, initial_dealer_cards)

            return _finish_game(game, engine, current_user, db)
        else:
            # Single-hand bust — resolve immediately (no dealer play needed)
            return _finish_game(game, engine, current_user, db)

    return _build_active_state(game, engine, current_user)


@router.post("/stand", response_model=GameState)
def stand(
    action: GameAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Player stands — dealer plays (or advance to next split hand) and game resolves."""

    game, engine = _get_active_game(action.game_id, current_user.id, db)

    stand_result = engine.player_stand()

    if stand_result == "next_hand":
        # Split game: more hands remain — return active state for next hand
        return _build_active_state(game, engine, current_user)

    # Final stand: dealer must play
    initial_dealer_cards = len(engine.dealer_hand.cards)
    engine.dealer_play()
    _save_dealer_cards(game.id, engine, db, initial_dealer_cards)

    return _finish_game(game, engine, current_user, db)


# ---------------------------------------------------------------------------
# Phase 1: Double Down
# ---------------------------------------------------------------------------


@router.post("/double-down", response_model=GameState)
def double_down(
    action: GameAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Player doubles down:
    - Requires exactly 2 cards on the current hand
    - Deducts an additional bet equal to the original
    - Deals exactly 1 card, then dealer auto-plays and game resolves
    """
    game, engine = _get_active_game(action.game_id, current_user.id, db)

    if not engine.can_double_down():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Double down only available on initial hand",
        )

    if current_user.balance < game.bet_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance to double down",
        )

    # Charge additional bet and double the stored bet amount
    current_user.balance -= Decimal(str(game.bet_amount))
    game.bet_amount = Decimal(str(game.bet_amount)) * 2

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
    _save_player_card(
        card,
        game.id,
        hand_index=engine.current_hand_index,
        order_index=existing_count,
        db=db,
    )

    # Persist any new dealer cards drawn during auto-play
    _save_dealer_cards(game.id, engine, db, initial_dealer_cards)

    db.commit()

    return _finish_game(game, engine, current_user, db)


# ---------------------------------------------------------------------------
# Phase 2: Split
# ---------------------------------------------------------------------------


@router.post("/split", response_model=GameState)
def split(
    action: GameAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Player splits their hand:
    - Requires 2 cards of identical rank
    - Deducts an additional bet equal to the original (one bet per hand)
    - Creates two independent hands, each dealt one additional card
    - For split aces: each hand gets exactly one card and both auto-stand
    """
    game, engine = _get_active_game(action.game_id, current_user.id, db)

    if not engine.can_split():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only split matching ranks",
        )

    if current_user.balance < game.bet_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance to split",
        )

    # Deduct additional bet for the second hand
    current_user.balance -= Decimal(str(game.bet_amount))

    # Perform the split (engine updates player_hands in place)
    card1, card2 = engine.player_split()

    # Persist cards: after split, hand 0 has [original_card, card1]
    #                             hand 1 has [split_card, card2]
    # The original cards are already in DB; we only need to save the two new dealt cards.
    existing_h0 = len(
        [c for c in game.cards if c.owner == "player" and c.hand_index == 0]
    )
    _save_player_card(card1, game.id, hand_index=0, order_index=existing_h0, db=db)

    existing_h1 = len(
        [c for c in game.cards if c.owner == "player" and c.hand_index == 1]
    )
    # Also persist the split card (the one moved to hand 1 from DB perspective)
    split_card = engine.player_hands[1].cards[0]  # original card moved to hand 1
    _save_player_card(split_card, game.id, hand_index=1, order_index=existing_h1, db=db)
    _save_player_card(card2, game.id, hand_index=1, order_index=existing_h1 + 1, db=db)

    db.commit()

    # Split aces: both hands auto-stand, dealer plays, game over
    if engine.split_aces:
        initial_dealer_cards = len(engine.dealer_hand.cards)
        engine.dealer_play()
        _save_dealer_cards(game.id, engine, db, initial_dealer_cards)
        return _finish_game(game, engine, current_user, db)

    return _build_active_state(game, engine, current_user)


# ---------------------------------------------------------------------------
# Read-only
# ---------------------------------------------------------------------------


@router.get("/{game_id}", response_model=GameState)
def get_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
            Game.user_id == current_user.id,
        )
        .first()
    )

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    # Reconstruct hands from database
    from app.services.game_engine import Hand
    from app.services.deck import Card

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
        bet_amount=game.bet_amount,
        player_hand=[
            CardSchema(rank=c.card_rank, suit=c.card_suit) for c in primary_player_cards
        ],
        player_value=player_hand.value(),
        dealer_hand=dealer_hand_display,
        dealer_value=dealer_value,
        result=game.result,
        payout=None,
        new_balance=float(current_user.balance),
        is_split=game.is_split,
    )
