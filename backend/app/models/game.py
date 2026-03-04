import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Index,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time import utc_now


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (Index("ix_games_user_status", "user_id", "status"),)

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, default="active", nullable=False)  # active, finished
    bet_amount = Column(Numeric(10, 2), nullable=False)
    result = Column(
        String, nullable=True
    )  # win, lose, push, blackjack (comma-sep for split)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    # Phase 2: track whether this game involved a split
    is_split = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="games")
    cards = relationship(
        "GameCard", back_populates="game", cascade="all, delete-orphan"
    )


class GameCard(Base):
    __tablename__ = "game_cards"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(Uuid(as_uuid=True), ForeignKey("games.id"), nullable=False)
    owner = Column(String, nullable=False)  # player, dealer
    card_rank = Column(String, nullable=False)
    card_suit = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    # Phase 2: which hand this card belongs to (0 = main/dealer, 1 = split hand)
    # Default 0 keeps all existing non-split games fully compatible.
    hand_index = Column(Integer, default=0, nullable=False)

    # Relationships
    game = relationship("Game", back_populates="cards")
