import logging
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.game import GameStart, GameState, GameAction
from app.services import game_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routes — thin layer delegating to game_service
# ---------------------------------------------------------------------------


@router.post("/start", response_model=GameState)
def start_game(
    game_data: GameStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new blackjack game."""
    return game_service.start_game(
        bet_amount=Decimal(str(game_data.bet_amount)),
        user=current_user,
        db=db,
    )


@router.post("/hit", response_model=GameState)
def hit(
    action: GameAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Player hits — request another card on the current hand."""
    return game_service.player_hit(action.game_id, current_user, db)


@router.post("/stand", response_model=GameState)
def stand(
    action: GameAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Player stands — dealer plays (or advance to next split hand) and game resolves."""
    return game_service.player_stand(action.game_id, current_user, db)


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
    return game_service.player_double_down(action.game_id, current_user, db)


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
    """
    return game_service.player_split(action.game_id, current_user, db)


@router.get("/{game_id}", response_model=GameState)
def get_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get game state by ID (reconstructed from DB)."""
    return game_service.get_game_by_id(game_id, current_user, db)
