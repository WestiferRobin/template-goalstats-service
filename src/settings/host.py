"""Explicit direct-script LOCAL configuration; never used by the general factory."""

import ipaddress
import os
import socket
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from flask import Flask
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from infra.resources.db import Database, is_ready
from infra.resources.redis import RedisCache
from settings.base import ConfigurationError, Settings

HOST_FILE = Path(__file__).resolve().parents[2] / ".env.host.local"
KEYS = frozenset(
    {
        "APP_ENV",
        "DATABASE_URL",
        "REDIS_URL",
        "CACHE_KEY_PREFIX",
        "CACHE_TTL_SECONDS",
        "LOG_LEVEL",
        "OPENAPI_ENABLED",
        "HOST_APP_PORT",
        "FLASK_DEBUG",
    }
)


def read_host_file(path: Path) -> dict[str, str]:
    """Read the generated literal KEY=value format without following symlinks."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ConfigurationError(
                    "LOCAL host configuration must be a private regular file owned by this user."
                )
            content = stream.read()
    except FileNotFoundError:
        raise ConfigurationError(
            "LOCAL host configuration is missing. Run make providers ENV=local."
        ) from None
    except (OSError, UnicodeError):
        raise ConfigurationError(
            "Cannot read private LOCAL host configuration; symlinks are not allowed."
        ) from None
    values: dict[str, str] = {}
    for line in content.splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in KEYS or key in values or "\x00" in value:
            raise ConfigurationError(
                "Invalid LOCAL host configuration: use unique supported KEY=value lines."
            )
        values[key] = value
    if values.get("APP_ENV", "").strip().lower() != "local":
        raise ConfigurationError("LOCAL host configuration must specify APP_ENV=local.")
    return values


def loopback(host: str | None) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def load_host_config(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if environ is None else environ
    if "APP_ENV" in source and source["APP_ENV"].strip().lower() != "local":
        raise ConfigurationError(
            "Direct src/main.py execution supports LOCAL only. "
            "Remove the conflicting APP_ENV setting."
        )
    values = {"APP_ENV": "local", "OPENAPI_ENABLED": "true", "HOST_APP_PORT": "5300"}
    values.update(read_host_file(HOST_FILE))
    values.update({key: source[key] for key in KEYS if key in source})
    values.update(APP_ENV="local", FLASK_DEBUG="0")
    settings = Settings.load(values)
    if not loopback(settings.database_url.host):
        raise ConfigurationError("DATABASE_URL for LOCAL host development must use loopback.")
    if settings.redis_url and not loopback(urlsplit(settings.redis_url).hostname):
        raise ConfigurationError("REDIS_URL for LOCAL host development must use loopback.")
    port = values["HOST_APP_PORT"]
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ConfigurationError("HOST_APP_PORT must be an integer from 1 to 65535.")
    return values


def check_app_port(port: int) -> None:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            raise ConfigurationError(
                f"LOCAL application port {port} is unavailable. Stop the other application "
                "or choose HOST_APP_PORT."
            ) from None


def diagnose_providers(app: Flask) -> None:
    """Bounded reads only. Schema readiness and cache fallback retain their policies."""
    database = cast(Database, app.extensions["goalstats_database"])
    cache = cast(RedisCache, app.extensions["goalstats_cache"])
    settings = cast(Settings, app.extensions["goalstats_settings"])
    try:
        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database.dispose()
        raise ConfigurationError(
            "LOCAL PostgreSQL is unavailable. Run make providers ENV=local "
            "and verify the existing configuration."
        ) from None
    if not is_ready(database):
        app.logger.warning(
            "LOCAL database is not ready. If migrations are pending, run make migrate ENV=local."
        )
    if not cache.ready(settings.cache_key_prefix):
        app.logger.warning(
            "LOCAL Redis is unavailable; database fallback remains active. "
            "Run make providers ENV=local."
        )
