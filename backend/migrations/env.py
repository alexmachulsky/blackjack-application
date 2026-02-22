"""
Alembic environment configuration.
Reads DATABASE_URL from the application settings so there is a single
source of truth — no URL duplication between app config and migrations.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Load app settings (reads from .env via pydantic-settings)
from app.core.config import settings

# Import all models so Alembic can detect schema changes via autogenerate
from app.core.database import Base
from app.models import user, game  # noqa: F401 — ensure models are registered

# Alembic Config object provides access to values in alembic.ini
alembic_config = context.config

# Inject the DATABASE_URL from app settings into Alembic config
alembic_config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure Python logging from the ini file
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without an active DB connection ('offline' mode).
    Generates SQL scripts without connecting.
    """
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations with an active DB connection ('online' mode — standard usage).
    """
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
