from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.game import Game
from app.schemas.stats import (
    GameHistoryResponse,
    GameHistoryItem,
    HistoryCard,
    PlayerStats,
)

router = APIRouter()


@router.get("/history", response_model=GameHistoryResponse)
def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated game history for the current user."""

    base_query = db.query(Game).filter(
        Game.user_id == current_user.id,
        Game.status == "finished",
    )

    total = base_query.count()

    games = (
        base_query.options(joinedload(Game.cards))
        .order_by(Game.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for g in games:
        sorted_cards = sorted(g.cards, key=lambda c: c.order_index)
        player_cards = [
            HistoryCard(
                rank=c.card_rank,
                suit=c.card_suit,
                owner=c.owner,
                hand_index=c.hand_index,
            )
            for c in sorted_cards
            if c.owner == "player"
        ]
        dealer_cards = [
            HistoryCard(
                rank=c.card_rank,
                suit=c.card_suit,
                owner=c.owner,
                hand_index=c.hand_index,
            )
            for c in sorted_cards
            if c.owner == "dealer"
        ]
        items.append(
            GameHistoryItem(
                game_id=str(g.id),
                bet_amount=float(g.bet_amount),
                result=g.result,
                is_split=g.is_split,
                created_at=g.created_at,
                player_cards=player_cards,
                dealer_cards=dealer_cards,
            )
        )

    return GameHistoryResponse(
        games=items,
        total=total,
        page=page,
        page_size=page_size,
    )


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
        current_balance=float(current_user.balance),
    )
