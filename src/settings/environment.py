"""Canonical private machine configuration and endpoint-free TEST policy (stdlib only)."""

import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path

SERVICE = "goalstats-template-py"
DATABASE = "goalstats_template_py"
POLICY_DEFAULTS = {"LOG_LEVEL": "INFO", "OPENAPI_ENABLED": "true", "CACHE_TTL_SECONDS": "300"}
PORT_DEFAULTS = {
    "HOST_APP_PORT": "5300",
    "LOCAL_APP_PORT": "5100",
    "DEV_APP_PORT": "5200",
    "LOCAL_POSTGRES_PORT": "55432",
    "LOCAL_REDIS_PORT": "56379",
}
LOCAL_KEYS = (
    frozenset(PORT_DEFAULTS)
    | frozenset(POLICY_DEFAULTS)
    | {"POSTGRES_PASSWORD", "DEV_POSTGRES_PASSWORD"}
)


class EnvironmentError(ValueError):
    """Credential-free configuration failure."""


def read_private(path: Path, keys: frozenset[str]) -> dict[str, str]:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise EnvironmentError(
                    f"{path.name}: configuration must be a private regular file owned by this user."
                )
            content = stream.read()
    except FileNotFoundError:
        kind = "LOCAL" if path.name == ".env.local" else "TEST"
        raise EnvironmentError(
            f"{path.name}: {kind} configuration is missing. Run make setup, then make providers."
        ) from None
    except (OSError, UnicodeError):
        raise EnvironmentError(
            f"{path.name}: cannot read private configuration; symlinks are forbidden."
        ) from None
    result: dict[str, str] = {}
    for number, line in enumerate(content.splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in keys or key in result or "\x00" in value:
            raise EnvironmentError(
                f"{path.name}:{number}: configuration requires unique supported KEY=value lines."
            )
        result[key] = value
    return result


def log_level(value: str) -> str:
    level = value.strip().upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise EnvironmentError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL.")
    return level


def boolean(value: str) -> bool:
    match value.strip().lower():
        case "true" | "1":
            return True
        case "false" | "0":
            return False
        case _:
            raise EnvironmentError("OPENAPI_ENABLED must be true, false, 1 or 0.")


def cache_ttl(value: str) -> int:
    try:
        result = int(value)
        if not 1 <= result <= 86400:
            raise ValueError
        return result
    except ValueError:
        raise EnvironmentError("CACHE_TTL_SECONDS must be an integer from 1 to 86400.") from None


def policy(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) - POLICY_DEFAULTS.keys():
        raise EnvironmentError(
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
    except EnvironmentError as exc:
        raise EnvironmentError(f"{path.name}: {exc}") from None


def machine(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) - LOCAL_KEYS:
        raise EnvironmentError(
            "Unsupported LOCAL machine key; run make setup to migrate legacy configuration."
        )
    result = {
        **PORT_DEFAULTS,
        **policy({k: v for k, v in values.items() if k in POLICY_DEFAULTS}),
        **values,
    }
    for key in ("POSTGRES_PASSWORD", "DEV_POSTGRES_PASSWORD"):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{16,128}", result.get(key, "")):
            raise EnvironmentError(
                f"{key} must be 16–128 URL-safe characters; preserve existing credentials."
            )
    for key in PORT_DEFAULTS:
        value = result[key]
        if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
            raise EnvironmentError(f"{key} must be a valid port number.")
    if len({int(result[k]) for k in PORT_DEFAULTS}) != len(PORT_DEFAULTS):
        raise EnvironmentError("Machine app/provider ports must be distinct.")
    return result


def load_machine(path: Path) -> dict[str, str]:
    values = read_private(path, LOCAL_KEYS)
    try:
        return machine(values)
    except EnvironmentError as exc:
        raise EnvironmentError(f"{path.name}: {exc}") from None


def application(values: Mapping[str, str], mode: str, *, host: bool = False) -> dict[str, str]:
    if mode not in {"local", "dev"} or (host and mode != "local"):
        raise EnvironmentError(
            "Machine configuration supports LOCAL/DEV only; host execution is LOCAL."
        )
    password = values["POSTGRES_PASSWORD" if mode == "local" else "DEV_POSTGRES_PASSWORD"]
    pg = "127.0.0.1:" + values["LOCAL_POSTGRES_PORT"] if host else "postgres:5432"
    redis = "127.0.0.1:" + values["LOCAL_REDIS_PORT"] if host else "redis:6379"
    return {
        **policy({k: v for k, v in values.items() if k in POLICY_DEFAULTS}),
        "APP_ENV": mode,
        "DATABASE_URL": f"postgresql+psycopg://goalstats:{password}@{pg}/{DATABASE}_{mode}",
        "REDIS_URL": f"redis://{redis}/0",
        "CACHE_KEY_PREFIX": f"{SERVICE}:{mode}:v1",
        "HOST_APP_PORT": values["HOST_APP_PORT"],
        "FLASK_DEBUG": "0",
    }
