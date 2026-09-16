"""Readiness policy, independent of Flask HTTP response construction."""

from typing import Literal

from infra.resources.db import Database, is_ready
from infra.resources.redis import RedisCache


def readiness(
    database: Database, cache: RedisCache, prefix: str
) -> Literal["Healthy", "Degraded", "Unhealthy"]:
    if not is_ready(database):
        return "Unhealthy"
    return "Healthy" if cache.ready(prefix) else "Degraded"
