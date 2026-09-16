"""Python migration environment sharing the application model metadata."""

from alembic import context
from sqlalchemy.engine import Connection

import models  # noqa: F401 — populate migration metadata
from infra.resources.db import Database
from models.base import Base
from settings.base import Settings

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=Settings.load().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied = context.config.attributes.get("connection")
    if isinstance(supplied, Connection):
        context.configure(connection=supplied, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    database = Database(Settings.load())
    try:
        with database.engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        database.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
