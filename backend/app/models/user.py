import uuid
from sqlalchemy import Column, String, Numeric, DateTime, Integer
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time import utc_now


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    balance = Column(Numeric(10, 2), default=1000.00, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Daily login bonus
    last_daily_bonus = Column(DateTime, nullable=True)
    daily_bonus_streak = Column(Integer, default=0, nullable=False, server_default="0")

    # Relationships
    games = relationship("Game", back_populates="user")
