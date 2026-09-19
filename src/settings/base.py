"""Validated settings. Explicit mappings never merge with the process environment."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from settings import environment


class ConfigurationError(ValueError):
    """A safe configuration message that never includes configuration values."""


def database_url(value: str) -> URL:
    try:
        url = make_url(value)
        if url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError
        if not url.host or not url.username or not url.database:
            raise ValueError
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError
        # Connection budgets and provider selection belong to this application.
        if url.query:
            raise ValueError
        return url.set(drivername="postgresql+psycopg")
    except (ArgumentError, ValueError, TypeError):
        raise ConfigurationError(
            "DATABASE_URL must be a PostgreSQL URL with host, username and database; "
            "query parameters are not supported."
        ) from None


def boolean(value: str) -> bool:
    try:
        return environment.boolean(value)
    except environment.EnvironmentError as exc:
        raise ConfigurationError(str(exc)) from None


def redis_url(value: str) -> str | None:
    if not value:
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in {"redis", "rediss"} or not url.hostname or url.query or url.fragment:
            raise ValueError
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError
        if url.path not in {"", "/"} and not re.fullmatch(r"/[0-9]+", url.path):
            raise ValueError
        return value
    except ValueError:
        raise ConfigurationError(
            "REDIS_URL must be a redis/rediss URL without query parameters."
        ) from None


def cache_ttl(value: str) -> int:
    try:
        return environment.cache_ttl(value)
    except environment.EnvironmentError as exc:
        raise ConfigurationError(str(exc)) from None


def cache_prefix(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9:_-]{0,99}", value):
        raise ConfigurationError("CACHE_KEY_PREFIX must be 1–100 safe namespace characters.")
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: URL = field(repr=False)
    log_level: str
    openapi_enabled: bool
    redis_url: str | None = field(default=None, repr=False)
    cache_key_prefix: str = "goalstats-template-py:local:v1"
    cache_ttl_seconds: int = 300

    @classmethod
    def load(cls, values: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if values is None else values
        env = source.get("APP_ENV", "local").strip().lower()
        if env not in {"local", "dev", "test"}:
            raise ConfigurationError("APP_ENV must be local, dev or test.")
        try:
            level = environment.log_level(
                source.get("LOG_LEVEL", environment.POLICY_DEFAULTS["LOG_LEVEL"])
            )
        except environment.EnvironmentError as exc:
            raise ConfigurationError(str(exc)) from None
        return cls(
            app_env=env,
            database_url=database_url(source.get("DATABASE_URL", "")),
            log_level=level,
            redis_url=redis_url(source.get("REDIS_URL", "")),
            cache_key_prefix=cache_prefix(
                source.get("CACHE_KEY_PREFIX", f"goalstats-template-py:{env}:v1")
            ),
            cache_ttl_seconds=cache_ttl(
                source.get("CACHE_TTL_SECONDS", environment.POLICY_DEFAULTS["CACHE_TTL_SECONDS"])
            ),
            openapi_enabled=boolean(source.get("OPENAPI_ENABLED", "false")),
        )
