"""Read-only machine port diagnosis; an existing exact Compose binding is expected."""

import socket

from environment_config import schema
from test_ownership import inspect_container


def check_database(stack):
    """Read-only authentication check, only when PostgreSQL is already running."""
    ids = stack.compose("ps", "-q", "postgres", capture=True).stdout.split()
    if not ids:
        return
    if len(ids) != 1:
        raise RuntimeError("Unexpected PostgreSQL container count; inspect the selected stack.")
    container = inspect_container(ids[0])
    labels = container["Config"]["Labels"]
    if (
        labels.get("com.docker.compose.project") != stack.project
        or labels.get("com.docker.compose.service") != "postgres"
    ):
        raise RuntimeError("PostgreSQL ownership mismatch; refusing diagnosis.")
    result = stack.compose(
        "exec",
        "-T",
        "-e",
        "PGPASSWORD=" + stack.settings["POSTGRES_PASSWORD"],
        "-e",
        "PGCONNECT_TIMEOUT=3",
        "postgres",
        "psql",
        "-h",
        "postgres",
        "-U",
        "goalstats",
        "-d",
        schema.DATABASE + "_" + stack.env,
        "-At",
        "-c",
        "SELECT 1",
        capture=True,
        check=False,
    )
    if result.returncode or result.stdout.strip() != "1":
        raise RuntimeError(
            f"{stack.env.upper()} PostgreSQL authentication/read failed. "
            "Restore original .env.local credentials; changing the file does not rotate a volume."
        )
    print(f"OK {stack.env.upper()} PostgreSQL authentication (read-only)")


def check_ports(root):
    from workflow import Stack

    values = schema.load_machine(root / ".env.local")
    for mode in ("local", "dev"):
        check_database(Stack(mode))
    expected = {
        "LOCAL_POSTGRES_PORT": ("local", "postgres", "5432/tcp"),
        "LOCAL_REDIS_PORT": ("local", "redis", "6379/tcp"),
        "LOCAL_APP_PORT": ("local", "app", "8000/tcp"),
        "DEV_APP_PORT": ("dev", "app", "8000/tcp"),
    }
    for key in schema.PORT_DEFAULTS:
        port = values[key]
        owned = False
        if key in expected:
            mode, service, internal = expected[key]
            stack = Stack(mode)
            ids = stack.compose("ps", "-q", service, capture=True).stdout.split()
            if len(ids) == 1:
                container = inspect_container(ids[0])
                labels = container["Config"]["Labels"]
                owned = (
                    container["State"]["Running"]
                    and labels.get("com.docker.compose.project") == stack.project
                    and labels.get("com.docker.compose.service") == service
                    and container["NetworkSettings"]["Ports"].get(internal)
                    == [{"HostIp": "127.0.0.1", "HostPort": port}]
                )
        if not owned:
            with socket.socket() as sock:
                try:
                    sock.bind(("127.0.0.1", int(port)))
                except OSError:
                    raise RuntimeError(
                        f".env.local {key}: port {port} is occupied. Stop the running host app "
                        "or conflicting process, or choose a free port in .env.local."
                    ) from None
        print(f"OK {key}: {'owned running container' if owned else 'available'}")
