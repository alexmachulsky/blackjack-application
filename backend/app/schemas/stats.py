from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PlayerStats(BaseModel):
    total_games: int
    wins: int
    losses: int
    pushes: int
    blackjacks: int
    win_rate: float
    current_balance: float


# ── Game History ──────────────────────────────────────────────────────────


class HistoryCard(BaseModel):
    rank: str
    suit: str
    owner: str  # "player" | "dealer"
    hand_index: int = 0


class GameHistoryItem(BaseModel):
    game_id: str
    bet_amount: float
    result: Optional[str]
    is_split: bool
    created_at: datetime
    player_cards: List[HistoryCard]
    dealer_cards: List[HistoryCard]


class GameHistoryResponse(BaseModel):
    games: List[GameHistoryItem]
    total: int
    page: int
    page_size: int
