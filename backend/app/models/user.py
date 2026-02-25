import uuid
from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    balance = Column(Numeric(10, 2), default=1000.00, nullable=False)
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    # Relationships
    games = relationship("Game", back_populates="user")
