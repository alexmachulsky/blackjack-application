from pydantic import BaseModel


class PlayerStats(BaseModel):
    total_games: int
    wins: int
    losses: int
    pushes: int
    blackjacks: int
    win_rate: float
    current_balance: float
