"""Bounded, best-effort Redis operations. No provider data is logged."""

import json
import logging
from typing import Any

from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from settings.redis import RedisSettings


class RedisCache:
    def __init__(self, settings: RedisSettings, logger: logging.Logger) -> None:
        self.logger = logger
        self.client: Redis | None = (
            Redis.from_url(
                settings.url,
                socket_connect_timeout=1,
                socket_timeout=1,
                retry=Retry(NoBackoff(), 0),
                max_connections=10,
                decode_responses=False,
            )
            if settings.url
            else None
        )

    def get(self, key: str) -> dict[str, Any] | None:
        if self.client is None:
            return None
        try:
            value = self.client.get(key)
            if value is None:
                return None
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else None
        except (RedisError, ValueError, TypeError):
            self.logger.warning("Cache read unavailable or invalid; using database fallback")
            return None

    def set(self, key: str, value: dict[str, Any], ttl: int) -> None:
        if self.client is None:
            return
        try:
            self.client.set(key, json.dumps(value, allow_nan=False), ex=ttl)
        except (RedisError, ValueError, TypeError):
            self.logger.warning("Cache write unavailable; database remains authoritative")

    def delete(self, key: str) -> None:
        if self.client is None:
            return
        try:
            self.client.delete(key)
        except RedisError:
            self.logger.warning("Cache invalidation unavailable; entry may remain until expiration")

    def ready(self, prefix: str) -> bool:
        if self.client is None:
            return False
        try:
            # Exercise the read capability used by this cache, not just PING.
            self.client.get(prefix + ":readiness")
            return True
        except RedisError:
            return False

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
