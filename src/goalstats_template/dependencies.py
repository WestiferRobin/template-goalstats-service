"""Flask composition boundary. Business code receives dependencies explicitly."""

from typing import cast

from flask import current_app, g
from sqlalchemy.orm import Session

from goalstats_template.infrastructure.database.session import Database
from goalstats_template.services.actions import ActionService
from goalstats_template.services.items import ItemService


def get_database() -> Database:
    return cast(Database, current_app.extensions["goalstats_database"])


def get_session() -> Session:
    """One lazy session per app context (normally one request), never auto-committed."""
    if "goalstats_session" not in g:
        g.goalstats_session = get_database().sessions()
    return cast(Session, g.goalstats_session)


def close_session(error: BaseException | None = None) -> None:
    session = g.pop("goalstats_session", None)
    if session is not None:
        # close() rolls back any uncommitted transaction and returns the connection.
        session.close()


def get_item_service() -> "ItemService":
    return ItemService(get_database(), current_app.extensions["goalstats_item_cache"])


def get_action_service() -> "ActionService":
    return ActionService(get_database(), current_app.extensions["goalstats_action_cache"])
