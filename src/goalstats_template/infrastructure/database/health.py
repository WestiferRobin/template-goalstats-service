"""Readiness requires the current migration and access to all mapped columns."""

from pathlib import Path

from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from goalstats_template.infrastructure.database.session import Database
from goalstats_template.models import Action, Item


def is_ready(database: Database) -> bool:
    try:
        expected = set(
            ScriptDirectory(str(Path(__file__).resolve().parents[4] / "migrations")).get_heads()
        )
        with database.engine.connect() as connection:
            if connection.scalar(text("SELECT current_database()")) != database.engine.url.database:
                return False
            if (
                not expected
                or set(MigrationContext.configure(connection).get_current_heads()) != expected
            ):
                return False
            connection.execute(select(Item).limit(1)).all()
            connection.execute(select(Action).limit(1)).all()
            return True
    except (SQLAlchemyError, OSError, CommandError):
        return False
