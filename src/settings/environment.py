"""Explicit private sources and typed composition; never a global settings singleton."""

import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from settings.base import ConfigurationError, ExecutionContext, boolean, loopback, port
from settings.core import POLICY_DEFAULTS as CORE_POLICY
from settings.core import PORT_DEFAULTS as CORE_PORTS
from settings.core import SERVICE as SERVICE
from settings.core import CoreSettings, environment, log_level
from settings.database import DATABASE as DATABASE
from settings.database import (
    PASSWORD_KEYS,
    DatabaseSettings,
    credentials,
    database_url,
    derive_database_url,
)
from settings.database import PORT_DEFAULTS as DB_PORTS
from settings.redis import POLICY_DEFAULTS as REDIS_POLICY
from settings.redis import PORT_DEFAULTS as REDIS_PORTS
from settings.redis import RedisSettings, cache_ttl, default_prefix, derive_redis_url

# These mappings are views of concern-owned defaults, also used by stdlib tooling.
POLICY_DEFAULTS = {**CORE_POLICY, **REDIS_POLICY}
PORT_DEFAULTS = {**CORE_PORTS, **DB_PORTS, **REDIS_PORTS}
LOCAL_KEYS = frozenset(PORT_DEFAULTS) | frozenset(POLICY_DEFAULTS) | PASSWORD_KEYS
LOCAL_FILE = Path(__file__).resolve().parents[2] / ".env.local"
DIRECT_KEYS = frozenset(
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


def read_private(path: Path, keys: frozenset[str]) -> dict[str, str]:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ConfigurationError(
                    f"{path.name}: configuration must be a private regular file owned by this user."
                )
            content = stream.read()
    except FileNotFoundError:
        kind = "LOCAL" if path.name == ".env.local" else "TEST"
        raise ConfigurationError(
            f"{path.name}: {kind} configuration is missing. Run make setup, then make providers."
        ) from None
    except (OSError, UnicodeError):
        raise ConfigurationError(
            f"{path.name}: cannot read private configuration; symlinks are forbidden."
        ) from None
    result: dict[str, str] = {}
    for number, line in enumerate(content.splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in keys or key in result or "\x00" in value:
            raise ConfigurationError(
                f"{path.name}:{number}: configuration requires unique supported KEY=value lines."
            )
        result[key] = value
    return result


def policy(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) - POLICY_DEFAULTS.keys():
        raise ConfigurationError(
            "TEST policy contains unsupported keys; provider configuration is forbidden."
        )
    result = {**POLICY_DEFAULTS, **values}
    result["LOG_LEVEL"] = log_level(result["LOG_LEVEL"])
    boolean(result["OPENAPI_ENABLED"])
    cache_ttl(result["CACHE_TTL_SECONDS"])
    return result


def test_policy(root: Path) -> dict[str, str]:
    path = root / ".env.test"
    values = (
        read_private(path, frozenset(POLICY_DEFAULTS)) if path.exists() or path.is_symlink() else {}
    )
    try:
        return policy(values)
    except ConfigurationError as exc:
        raise ConfigurationError(f"{path.name}: {exc}") from None


def machine(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) - LOCAL_KEYS:
        raise ConfigurationError(
            "Unsupported LOCAL machine key; run make setup to migrate legacy configuration."
        )
    result = {
        **PORT_DEFAULTS,
        **policy({k: v for k, v in values.items() if k in POLICY_DEFAULTS}),
        **values,
    }
    credentials(result)
    for key in PORT_DEFAULTS:
        port(result[key], key)
    if len({int(result[k]) for k in PORT_DEFAULTS}) != len(PORT_DEFAULTS):
        raise ConfigurationError("Machine app/provider ports must be distinct.")
    return result


def load_machine(path: Path) -> dict[str, str]:
    values = read_private(path, LOCAL_KEYS)
    try:
        return machine(values)
    except ConfigurationError as exc:
        raise ConfigurationError(f"{path.name}: {exc}") from None


def application(values: Mapping[str, str], mode: str, *, host: bool = False) -> dict[str, str]:
    if mode not in {"local", "dev"} or (host and mode != "local"):
        raise ConfigurationError(
            "Machine configuration supports LOCAL/DEV only; host execution is LOCAL."
        )
    context: ExecutionContext = "host" if host else "container"
    return {
        **policy({k: v for k, v in values.items() if k in POLICY_DEFAULTS}),
        "APP_ENV": mode,
        "DATABASE_URL": derive_database_url(values, mode, context=context),
        "REDIS_URL": derive_redis_url(values, context=context),
        "CACHE_KEY_PREFIX": default_prefix(mode),
        "HOST_APP_PORT": values["HOST_APP_PORT"],
        "FLASK_DEBUG": "0",
    }


@dataclass(frozen=True)
class Settings:
    core: CoreSettings
    database: DatabaseSettings
    redis: RedisSettings

    def __post_init__(self) -> None:
        if not (
            isinstance(self.core, CoreSettings)
            and isinstance(self.database, DatabaseSettings)
            and isinstance(self.redis, RedisSettings)
        ):
            raise ConfigurationError("Settings require validated core, database and Redis groups.")


def load_application(values: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if values is None else values
    mode = environment(source.get("APP_ENV", "local"))
    return Settings(
        CoreSettings(
            mode,
            log_level(source.get("LOG_LEVEL", CORE_POLICY["LOG_LEVEL"])),
            boolean(source.get("OPENAPI_ENABLED", "false")),
            port(source.get("HOST_APP_PORT", CORE_PORTS["HOST_APP_PORT"]), "HOST_APP_PORT"),
        ),
        DatabaseSettings(database_url(source.get("DATABASE_URL", ""))),
        RedisSettings(
            source.get("REDIS_URL") or None,
            source.get("CACHE_KEY_PREFIX", default_prefix(mode)),
            cache_ttl(source.get("CACHE_TTL_SECONDS", REDIS_POLICY["CACHE_TTL_SECONDS"])),
        ),
    )


def load_local(environ: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    if "APP_ENV" in source and source["APP_ENV"].strip().lower() != "local":
        raise ConfigurationError(
            "Direct execution supports LOCAL only. Remove the conflicting APP_ENV setting."
        )
    values = application(load_machine(LOCAL_FILE), "local", host=True)
    values.update({key: source[key] for key in DIRECT_KEYS if key in source})
    values.update(APP_ENV="local", FLASK_DEBUG="0")
    result = load_application(values)
    if not loopback(result.database.url.host):
        raise ConfigurationError("DATABASE_URL for LOCAL host development must use loopback.")
    if result.redis.url and not loopback(urlsplit(result.redis.url).hostname):
        raise ConfigurationError("REDIS_URL for LOCAL host development must use loopback.")
    return result
