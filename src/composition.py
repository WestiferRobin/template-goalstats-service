"""Flask-only dependency wiring; application services receive concrete resources."""

from typing import cast

from flask import current_app

from infra.resources.db import Database
from infra.resources.redis import RedisCache
from services.item.action import ActionService
from services.item.item import ItemService
from settings.base import Settings


def get_database() -> Database:
    return cast(Database, current_app.extensions["goalstats_database"])


def get_cache() -> RedisCache:
    return cast(RedisCache, current_app.extensions["goalstats_cache"])


def get_settings() -> Settings:
    return cast(Settings, current_app.extensions["goalstats_settings"])


def get_item_service() -> ItemService:
    return ItemService(get_database(), current_app.extensions["goalstats_item_cache"])


def get_action_service() -> ActionService:
    return ActionService(get_database(), current_app.extensions["goalstats_action_cache"])
