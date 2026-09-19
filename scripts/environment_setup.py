"""Create/migrate private configuration, preserving credentials before retiring old files."""

import errno
import fcntl
import os
import secrets
import tempfile
from pathlib import Path

from environment_config import schema

LEGACY_KEYS = frozenset(
    {"POSTGRES_PASSWORD", "APP_PORT", "HOST_APP_PORT", "LOCAL_POSTGRES_PORT", "LOCAL_REDIS_PORT"}
)
HOST_KEYS = frozenset(
    {
        "APP_ENV",
        "DATABASE_URL",
        "REDIS_URL",
        "CACHE_KEY_PREFIX",
        "HOST_APP_PORT",
        "FLASK_DEBUG",
        *schema.POLICY_DEFAULTS,
    }
)


def private_write(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def text(values):
    return "".join(f"{key}={value}\n" for key, value in values.items())


def setup_files(root, *, has_volume, verify):
    descriptor = os.open(root, os.O_RDONLY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another setup is active; wait for it to finish.") from None
        _setup_files(root, has_volume=has_volume, verify=verify)
    finally:
        os.close(descriptor)


def _setup_files(root, *, has_volume, verify):
    root = Path(root)
    local, dev, host, test = (
        root / name for name in (".env.local", ".env.dev", ".env.host.local", ".env.test")
    )
    # Validate everything before writing anything, including optional TEST policy.
    test_values = schema.test_policy(root)
    old = {}
    for path, keys in (
        (local, schema.LOCAL_KEYS | LEGACY_KEYS),
        (dev, LEGACY_KEYS),
        (host, HOST_KEYS),
    ):
        if path.exists() or path.is_symlink():
            old[path] = schema.read_private(path, keys)
    for path in (local, dev):
        if path in old and "POSTGRES_PASSWORD" not in old[path]:
            raise RuntimeError("Existing credentials are missing; restore them before setup.")
    if (
        local in old
        and "APP_PORT" not in old[local]
        and "DEV_POSTGRES_PASSWORD" not in old[local]
        and dev not in old
    ):
        raise RuntimeError("Canonical configuration is missing DEV credentials; restore them.")
    values = dict(old.get(local, {}))
    if "APP_PORT" in values:
        if "LOCAL_APP_PORT" in values and values["LOCAL_APP_PORT"] != values["APP_PORT"]:
            raise RuntimeError("Conflicting LOCAL app ports; existing files preserved.")
        values["LOCAL_APP_PORT"] = values.pop("APP_PORT")
    for mode, key in (("local", "POSTGRES_PASSWORD"), ("dev", "DEV_POSTGRES_PASSWORD")):
        previous = old.get(dev, {}).get("POSTGRES_PASSWORD") if mode == "dev" else None
        if previous:
            if key in values and values[key] != previous:
                raise RuntimeError("Conflicting DEV credentials; existing files preserved.")
            values[key] = previous
        if key not in values:
            if has_volume(mode):
                raise RuntimeError(
                    "Existing volume needs its original credentials. Restore configuration."
                )
            values[key] = secrets.token_hex(24)
    if dev in old:
        port = old[dev].get("APP_PORT")
        if not port:
            raise RuntimeError("Legacy DEV app port is missing; existing files preserved.")
        if "DEV_APP_PORT" in values and values["DEV_APP_PORT"] != port:
            raise RuntimeError("Conflicting DEV app ports; existing files preserved.")
        values["DEV_APP_PORT"] = port
    values = schema.machine(values)
    if host in old:
        if not {"APP_ENV", "DATABASE_URL"} <= old[host].keys():
            raise RuntimeError("Legacy host configuration is incomplete; files preserved.")
        derived = schema.application(values, "local", host=True)
        for key, value in old[host].items():
            if key in schema.POLICY_DEFAULTS:
                if key in old.get(local, {}) and old[local][key] != value:
                    raise RuntimeError("Conflicting LOCAL preferences; existing files preserved.")
                values[key] = value
            elif derived.get(key) != value:
                raise RuntimeError(
                    "Legacy host configuration conflicts with machine values; files preserved."
                )
        values = schema.machine(values)
    migrating = bool(dev in old or host in old or "APP_PORT" in old.get(local, {}))
    if migrating:
        # Existing volumes are authenticated before either configuration replacement or retirement.
        for mode in ("local", "dev"):
            if has_volume(mode):
                verify(mode, values)
    if local in old and not migrating:
        schema.machine(old[local])
    else:
        if old:
            internal = root / ".host-sessions"
            internal.mkdir(mode=0o700, exist_ok=True)
            if (
                internal.is_symlink()
                or internal.stat().st_uid != os.getuid()
                or internal.stat().st_mode & 0o077
            ):
                raise RuntimeError("Internal migration directory must be private and user-owned.")
            backup = Path(tempfile.mkdtemp(prefix="migration-", dir=internal))
            for path in old:
                private_write(backup / (path.name + ".backup"), path.read_text())
        internal = root / ".host-sessions"
        created_internal = not internal.exists()
        internal.mkdir(mode=0o700, exist_ok=True)
        if (
            internal.is_symlink()
            or internal.stat().st_uid != os.getuid()
            or internal.stat().st_mode & 0o077
        ):
            raise RuntimeError("Internal configuration state must be private and user-owned.")
        fd, temporary = tempfile.mkstemp(prefix="config-write-", dir=internal)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(text(values))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, local)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
            if created_internal:
                try:
                    internal.rmdir()
                except OSError as exc:
                    if exc.errno != errno.ENOTEMPTY:
                        raise
        for path in (dev, host):
            if path in old:
                path.unlink()
    if not test.exists():
        private_write(test, text(test_values))
    print("Private .env.local and .env.test ready; existing credentials preserved.")
