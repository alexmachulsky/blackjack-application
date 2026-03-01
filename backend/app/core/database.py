from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

_engine_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # TestClient and local scripts may access SQLite connections across threads.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

# Production pool tuning — prevents stale/dropped connections
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# SQLAlchemy 2.0 style — replaces the deprecated declarative_base() function
class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
