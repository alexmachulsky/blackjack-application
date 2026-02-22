from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.game import Game
from app.schemas.stats import PlayerStats

router = APIRouter()


@router.get("", response_model=PlayerStats)
def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get player statistics"""
    
    # Count games
    total_games = db.query(func.count(Game.id)).filter(
        Game.user_id == current_user.id,
        Game.status == "finished"
    ).scalar() or 0
    
    # Count wins
    wins = db.query(func.count(Game.id)).filter(
        Game.user_id == current_user.id,
        Game.result.in_(["win", "blackjack"])
    ).scalar() or 0
    
    # Count losses
    losses = db.query(func.count(Game.id)).filter(
        Game.user_id == current_user.id,
        Game.result == "lose"
    ).scalar() or 0
    
    # Count pushes
    pushes = db.query(func.count(Game.id)).filter(
        Game.user_id == current_user.id,
        Game.result == "push"
    ).scalar() or 0
    
    # Count blackjacks
    blackjacks = db.query(func.count(Game.id)).filter(
        Game.user_id == current_user.id,
        Game.result == "blackjack"
    ).scalar() or 0
    
    # Calculate win rate
    win_rate = (wins / total_games * 100) if total_games > 0 else 0.0
    
    return PlayerStats(
        total_games=total_games,
        wins=wins,
        losses=losses,
        pushes=pushes,
        blackjacks=blackjacks,
        win_rate=round(win_rate, 2),
        current_balance=current_user.balance
    )
