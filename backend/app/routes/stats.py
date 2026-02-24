from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.game import Game
from app.schemas.stats import PlayerStats

router = APIRouter()


@router.get("", response_model=PlayerStats)
def get_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get player statistics"""

    finished_results = (
        db.query(Game.result)
        .filter(Game.user_id == current_user.id, Game.status == "finished")
        .all()
    )

    total_games = len(finished_results)
    wins = 0
    losses = 0
    pushes = 0
    blackjacks = 0

    for (result_value,) in finished_results:
        if not result_value:
            continue

        hand_results = [part.strip().lower() for part in result_value.split(",")]

        for hand_result in hand_results:
            if hand_result == "blackjack":
                blackjacks += 1
                wins += 1
            elif hand_result == "win":
                wins += 1
            elif hand_result == "lose":
                losses += 1
            elif hand_result == "push":
                pushes += 1

    total_resolved_hands = wins + losses + pushes
    win_rate = (wins / total_resolved_hands * 100) if total_resolved_hands > 0 else 0.0

    return PlayerStats(
        total_games=total_games,
        wins=wins,
        losses=losses,
        pushes=pushes,
        blackjacks=blackjacks,
        win_rate=round(win_rate, 2),
        current_balance=current_user.balance,
    )
