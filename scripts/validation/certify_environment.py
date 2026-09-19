"""Disposable migration certification; optional source contains private legacy config only."""

import secrets
import tempfile
from pathlib import Path

from environment_config import schema
from environment_setup import private_write, setup_files, text
from workflow import assert_absent, fresh


def certify_environment(source=None):
    stacks = {mode: fresh(mode) for mode in ("local", "dev")}
    marker = secrets.token_hex(12)
    try:
        with tempfile.TemporaryDirectory(prefix="environment-migration-") as directory:
            root = Path(directory)
            for mode in stacks:
                path = root / (".env." + mode)
                if source is not None:
                    content = (Path(source) / path.name).read_text()
                else:
                    content = text(
                        {
                            "POSTGRES_PASSWORD": secrets.token_hex(24),
                            "APP_PORT": schema.PORT_DEFAULTS[mode.upper() + "_APP_PORT"],
                        }
                    )
                private_write(path, content)
            local = schema.read_private(
                root / ".env.local",
                frozenset(
                    {
                        "POSTGRES_PASSWORD",
                        "APP_PORT",
                        "HOST_APP_PORT",
                        "LOCAL_POSTGRES_PORT",
                        "LOCAL_REDIS_PORT",
                    }
                ),
            )
            dev = schema.read_private(
                root / ".env.dev", frozenset({"POSTGRES_PASSWORD", "APP_PORT"})
            )
            host_path = root / ".env.host.local"
            if source is not None and (Path(source) / host_path.name).exists():
                private_write(host_path, (Path(source) / host_path.name).read_text())
            else:
                machine = schema.machine(
                    {
                        "POSTGRES_PASSWORD": local["POSTGRES_PASSWORD"],
                        "DEV_POSTGRES_PASSWORD": dev["POSTGRES_PASSWORD"],
                        "LOCAL_APP_PORT": local["APP_PORT"],
                        "DEV_APP_PORT": dev["APP_PORT"],
                    }
                )
                private_write(host_path, text(schema.application(machine, "local", host=True)))
            old = {p.name: p.read_bytes() for p in root.iterdir()}
            for mode, original in (("local", local), ("dev", dev)):
                stack = stacks[mode]
                stack.settings["POSTGRES_PASSWORD"] = original["POSTGRES_PASSWORD"]
                stack.process_env["POSTGRES_PASSWORD"] = original["POSTGRES_PASSWORD"]
                stack.providers()
                stack.compose(
                    "exec",
                    "-T",
                    "postgres",
                    "psql",
                    "-U",
                    "goalstats",
                    "-d",
                    schema.DATABASE + "_" + mode,
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "CREATE TABLE environment_migration_probe (marker text); "
                    "INSERT INTO environment_migration_probe VALUES ('" + marker + "');",
                    capture=True,
                )

            def verify(mode, values):
                password = values[
                    "POSTGRES_PASSWORD" if mode == "local" else "DEV_POSTGRES_PASSWORD"
                ]
                result = stacks[mode].compose(
                    "exec",
                    "-T",
                    "-e",
                    "PGPASSWORD=" + password,
                    "postgres",
                    "psql",
                    "-h",
                    "postgres",
                    "-U",
                    "goalstats",
                    "-d",
                    schema.DATABASE + "_" + mode,
                    "-At",
                    "-c",
                    "SELECT marker FROM environment_migration_probe",
                    capture=True,
                    check=False,
                )
                assert result.returncode == 0 and result.stdout.strip() == marker, (
                    "Migration authentication/data verification failed"
                )

            setup_files(root, has_volume=lambda _: True, verify=verify)
            values = schema.load_machine(root / ".env.local")
            assert values["POSTGRES_PASSWORD"] == local["POSTGRES_PASSWORD"]
            assert values["DEV_POSTGRES_PASSWORD"] == dev["POSTGRES_PASSWORD"]
            assert values["LOCAL_APP_PORT"] == local["APP_PORT"]
            assert values["DEV_APP_PORT"] == dev["APP_PORT"]
            for mode in stacks:
                verify(mode, values)
            backup = next((root / ".host-sessions").glob("migration-*"))
            assert all(
                (backup / (name + ".backup")).read_bytes() == content
                for name, content in old.items()
            )
            before = (root / ".env.local").read_bytes()
            setup_files(root, has_volume=lambda _: True, verify=verify)
            assert before == (root / ".env.local").read_bytes()
            assert not (root / ".env.dev").exists()
        print(
            "Environment migration: PASS (credentials, ports, data, backups, idempotence)",
            flush=True,
        )
    finally:
        for stack in stacks.values():
            stack.stop(volumes=True)
            assert_absent(stack.project)
