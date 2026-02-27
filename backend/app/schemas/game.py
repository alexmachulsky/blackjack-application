from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
import uuid


class CardSchema(BaseModel):
    rank: str
    suit: str


class GameStart(BaseModel):
    bet_amount: float


# ---------------------------------------------------------------------------
# Phase 2: Per-hand state for split games
# ---------------------------------------------------------------------------


class HandState(BaseModel):
    """Represents the state of a single hand in a (possibly split) game."""

    cards: List[CardSchema]
    value: int
    # active | stood | bust | blackjack
    status: str
    can_double_down: bool


# ---------------------------------------------------------------------------
# Core game state — backward-compat fields kept, new fields optional/defaulted
# ---------------------------------------------------------------------------


class GameState(BaseModel):
    game_id: str
    status: str
    bet_amount: float
    # Backward-compat: always the current/first player hand
    player_hand: List[CardSchema]
    player_value: int
    dealer_hand: List[CardSchema]
    dealer_value: int
    result: Optional[str] = None
    payout: Optional[float] = None
    new_balance: Optional[float] = None

    # Phase 1: Double Down
    can_double_down: bool = False

    # Phase 2: Split
    is_split: bool = False
    can_split: bool = False
    # Populated only for split games
    player_hands: Optional[List[HandState]] = None
    current_hand_index: Optional[int] = None
    # Per-hand results/payouts when game finishes with a split
    results: Optional[List[str]] = None
    payouts: Optional[List[float]] = None


class GameAction(BaseModel):
    game_id: str


class GameResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    bet_amount: float
    result: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
