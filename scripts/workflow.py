"""Small Docker workflow shared by Make, smoke, and certification (standard library only)."""

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "goalstats-template-py:tooling"
HELP = """GoalStats Flask — LOCAL reloads mounted source; DEV runs built Gunicorn.
SETUP     make doctor                Read-only prerequisite and setup diagnosis
          make setup                 Verify tools; create missing private env files
          make build ENV=local|dev   Build the selected runtime
RUNTIME   make run ENV=local|dev     Start and wait for exactly 200 Healthy
IDE       make providers ENV=local  Healthy LOCAL providers + private host env; no app/migration
          make providers-stop ENV=local Stop providers only; preserve data
          make test-providers        Foreground owned disposable host TEST session
          make certify-host PYTHON=.venv/bin/python  Automated host acceptance (no IDE UI)
          make stop ENV=local|dev    Remove selected containers/network; retain DB volume
          make logs ENV=local|dev    Show recent selected-stack logs
DATABASE  make migrate ENV=local|dev Upgrade selected database to Alembic head
          make migration MESSAGE=\"description\"  Generate LOCAL revision for review
          make migration-check ENV=local|dev     Check selected database model drift
TEST      make unit                  Provider-independent unit suite
          make integration           Isolated TEST providers and integration suite
          make test                  Unit + integration once, isolated TEST providers
          make coverage              Same full suite with terminal coverage
          make smoke                 Disposable built DEV HTTP smoke
          make certify               Quality, tooling, coverage, built smoke, lifecycle checks
          make tooling               Workflow tests only (no providers)
QUALITY   make check                 Ruff lint/format check and strict mypy
Default ENV=local. Unknown environments are refused. No command auto-commits.
"""


def run(args, *, capture=False, env=None, check=True):
    """Terminate/reap the CLI child before outer resource cleanup on interruption."""
    process = subprocess.Popen(
        [str(a) for a in args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    try:
        stdout, stderr = process.communicate()
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    if check and process.returncode:
        # Do not print Compose config/command arguments, which can contain credentials.
        if capture and stderr:
            print(stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(process.returncode, args[0])
    return subprocess.CompletedProcess(args[0], process.returncode, stdout, stderr)


def interrupted(signum, _frame):
    raise SystemExit(128 + signum)


def install_signals():
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)


def setup(directory=ROOT):
    for tool in ("docker", "make"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"Required tool missing: {tool}")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Python 3.12 is required for host orchestration and the application")
    run(["docker", "compose", "version"])
    run(["docker", "info"], capture=True)
    for env, port in (("local", 5100), ("dev", 5200)):
        path = directory / f".env.{env}"
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            print(f"Preserved existing {path.name}")
            continue
        with os.fdopen(fd, "w") as stream:
            stream.write(f"POSTGRES_PASSWORD={secrets.token_hex(24)}\nAPP_PORT={port}\n")
        print(f"Created private {path.name}")
    print("Next: make build ENV=local; make migrate ENV=local; make run ENV=local")


def read_settings(path):
    if not path.exists():
        raise RuntimeError("Missing environment file; run make setup")
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, sep, value = line.partition("=")
            if (
                not sep
                or key
                not in {
                    "POSTGRES_PASSWORD",
                    "APP_PORT",
                    "HOST_APP_PORT",
                    "LOCAL_POSTGRES_PORT",
                    "LOCAL_REDIS_PORT",
                }
                or key in values
            ):
                raise RuntimeError("Environment file contains an unknown or duplicate key")
            values[key] = value
    if not re.fullmatch(r"[a-zA-Z0-9_-]{16,128}", values.get("POSTGRES_PASSWORD", "")):
        raise RuntimeError("POSTGRES_PASSWORD must be 16–128 URL-safe characters")
    for key in ("APP_PORT", "HOST_APP_PORT", "LOCAL_POSTGRES_PORT", "LOCAL_REDIS_PORT"):
        if key == "APP_PORT" or key in values:
            port = values.get(key, "")
            if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
                raise RuntimeError(f"{key} must be a valid port number")
    return values


class Stack:
    def __init__(self, env, *, project=None, settings=None):
        if env not in {"local", "dev", "test"}:
            raise RuntimeError("ENV must be local or dev (TEST is managed automatically)")
        self.env = env
        self.project = project or f"goalstats-template-py-{env}"
        self.disposable = project is not None
        if self.disposable and not re.fullmatch(
            r"goalstats-template-py-(test|cert)-[a-f0-9]+", project
        ):
            raise RuntimeError("Disposable project must use a unique owned test/cert identity")
        self.settings = settings if settings is not None else read_settings(ROOT / f".env.{env}")
        # Ignore ambient application/Compose settings, and never source shell env files.
        self.process_env = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}
        self.process_env.update(self.settings)
        # Optional LOCAL settings must never come from ambient shell variables.
        for key, default in (("LOCAL_POSTGRES_PORT", "55432"), ("LOCAL_REDIS_PORT", "56379")):
            self.process_env[key] = self.settings.get(key, default)
        self.args = [
            "docker",
            "compose",
            "--env-file",
            os.devnull,
            "-p",
            self.project,
            "-f",
            ROOT / "docker" / f"compose.{env}.yml",
        ]
        self.service = "runner" if env == "test" else "app"

    def compose(self, *args, **kwargs):
        return run([*self.args, *args], env=self.process_env, **kwargs)

    def providers(self):
        self.compose("up", "-d", "--wait", "--wait-timeout", "60", "postgres", "redis")

    def command(self, *args, options=(), **kwargs):
        name = self.project + "-oneoff-" + secrets.token_hex(6)
        try:
            with tempfile.TemporaryDirectory() as directory:
                compose_options = ()
                if self.env == "test":
                    receipt = Path(directory) / "owned-test.json"
                    receipt.write_text(
                        json.dumps(
                            {
                                "hostname": name,
                                "TEST_DATABASE_URL": "postgresql+psycopg://goalstats:"
                                + self.settings["POSTGRES_PASSWORD"]
                                + "@postgres:5432/goalstats_test_runtime",
                                "TEST_REDIS_URL": "redis://redis:6379/0",
                            }
                        )
                    )
                    # The enclosing directory is 0700; the non-root runner reads the mount.
                    receipt.chmod(0o444)
                    override = Path(directory) / "runner.json"
                    override.write_text(
                        json.dumps(
                            {
                                "services": {
                                    "runner": {
                                        "hostname": name,
                                        "volumes": [f"{receipt}:/run/owned-test.json:ro"],
                                    }
                                }
                            }
                        )
                    )
                    compose_options = ("-f", override)
                return run(
                    [
                        *self.args,
                        *compose_options,
                        "run",
                        "--rm",
                        "--no-deps",
                        "-T",
                        "--name",
                        name,
                        *options,
                        self.service,
                        *args,
                    ],
                    env=self.process_env,
                    **kwargs,
                )
        finally:
            run(["docker", "rm", "-f", name], capture=True, check=False)

    def migrate(self):
        self.providers()
        self.command("alembic", "upgrade", "head")

    def start(self):
        self.compose("up", "-d", "--wait", "--wait-timeout", "90", "app")
        wait_ready(self.url)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.settings['APP_PORT']}"

    def stop(self, *, volumes=False):
        if volumes and not self.disposable:
            raise RuntimeError("Refusing removal of persistent developer volumes")
        # A second signal must not interrupt resource cleanup.
        old = {s: signal.signal(s, signal.SIG_IGN) for s in (signal.SIGTERM, signal.SIGINT)}
        try:
            self.compose(
                "down", "--remove-orphans", "--timeout", "15", *(["--volumes"] if volumes else [])
            )
        finally:
            for sig, handler in old.items():
                signal.signal(sig, handler)


def inventory():
    return {
        kind: set(run(command, capture=True).stdout.splitlines())
        for kind, command in {
            "containers": ["docker", "ps", "-aq", "--no-trunc"],
            "images": ["docker", "image", "ls", "-a", "-q", "--no-trunc"],
            "networks": ["docker", "network", "ls", "-q", "--no-trunc"],
            "volumes": ["docker", "volume", "ls", "-q"],
        }.items()
    }


def assert_absent(project):
    label = "label=com.docker.compose.project=" + project
    for command in (
        ["docker", "ps", "-aq", "--filter", label],
        ["docker", "network", "ls", "-q", "--filter", label],
        ["docker", "volume", "ls", "-q", "--filter", label],
    ):
        assert not run(command, capture=True).stdout.strip(), f"Leaked resource in {project}"


def fresh(env):
    # Port allocation is checked by Docker at startup; a competing bind fails safely.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return Stack(
        env,
        project="goalstats-template-py-cert-" + secrets.token_hex(6),
        settings={
            "POSTGRES_PASSWORD": secrets.token_hex(24),
            "APP_PORT": str(port),
            "LOCAL_POSTGRES_PORT": "0",
            "LOCAL_REDIS_PORT": "0",
        },
    )


def wait_ready(url, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(url + "/ready", timeout=2) as response:
                if response.status == 200 and response.read() == b"Healthy":
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Startup requires HTTP 200 and exact Healthy; readiness timed out")


def build_tooling():
    run(["docker", "build", "--target", "tooling", "-t", IMAGE, "."])


def tool_command(*command):
    name = "goalstats-template-py-tool-" + secrets.token_hex(6)
    try:
        run(["docker", "run", "--rm", "--name", name, "--network", "none", IMAGE, *command])
    finally:
        run(["docker", "rm", "-f", name], capture=True, check=False)


def tests(mode, *, fault=None, project=None):
    build_tooling()
    if mode in {"unit", "tooling"}:
        target = "tests/unit" if mode == "unit" else "scripts/tests"
        tool_command("pytest", "-q", "-p", "no:cacheprovider", target)
        return
    stack = Stack(
        "test",
        project=project or "goalstats-template-py-test-" + secrets.token_hex(6),
        settings={"POSTGRES_PASSWORD": secrets.token_hex(24)},
    )
    try:
        if fault == "provider":
            # Real failed provider startup under the same finally/ownership boundary.
            with tempfile.TemporaryDirectory() as directory:
                override = Path(directory) / "failure.yml"
                override.write_text('services:\n  postgres:\n    command: ["false"]\n')
                stack.args += ["-f", override]
                try:
                    stack.providers()
                finally:
                    stack.args = stack.args[:-2]
        else:
            stack.providers()
        stack.command("alembic", "upgrade", "missing_revision" if fault == "migration" else "head")
        if fault == "signal":
            print("SIGNAL_TEST_RUNNING", flush=True)
            stack.command("python", "-c", "import time; time.sleep(300)")
        targets = (
            ["tests/integration"] if mode == "integration" else ["tests/unit", "tests/integration"]
        )
        command = ["pytest", "-q", "-p", "no:cacheprovider", *targets]
        if fault in {"unit", "integration"}:
            command = ["pytest", "-q", "-p", "no:cacheprovider", "tests/" + fault]
            command += ["-o", "required_plugins=goalstats_deliberately_missing_plugin"]
        if mode == "coverage":
            command += ["--cov=src", "--cov-report=term-missing"]
        stack.command(*command)
    finally:
        stack.stop(volumes=True)


def check():
    build_tooling()
    tool_command("ruff", "check", "--no-cache", ".")
    tool_command("ruff", "format", "--check", "--no-cache", ".")
    tool_command("mypy", "--cache-dir=/tmp/mypy-cache")


def doctor():
    """Read-only prerequisites and private configuration validation."""
    interpreter = shutil.which("python3.12")
    if interpreter is None and sys.version_info[:2] == (3, 12):
        interpreter = sys.executable
    if interpreter is None:
        raise RuntimeError("Python 3.12 is unavailable; install it before setup")
    run([interpreter, "--version"])
    for tool in ("docker", "make"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"Required tool missing: {tool}")
    run(["docker", "compose", "version"])
    run(["docker", "info"], capture=True)
    for name in (
        "requirements.txt",
        "Dockerfile",
        "Makefile",
        "alembic.ini",
        "alembic/env.py",
        "docker/compose.local.yml",
        "docker/compose.dev.yml",
        "docker/compose.test.yml",
    ):
        if not (ROOT / name).is_file():
            raise RuntimeError(f"Required repository file missing: {name}")
    for env in ("local", "dev"):
        read_settings(ROOT / f".env.{env}")
        print(f"OK {env.upper()} private configuration")
    print("Doctor: PASS (read-only)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command")
    parser.add_argument("--env", default=os.environ.get("ENV", "local"), choices=("local", "dev"))
    args = parser.parse_args()
    if args.env not in {"local", "dev"}:
        parser.error("ENV must be local or dev")
    install_signals()
    command = args.command
    if command == "help":
        print(HELP)
    elif command == "setup":
        setup()
    elif command == "doctor":
        doctor()
    elif command in {"providers", "providers-stop"}:
        if args.env != "local":
            raise RuntimeError("Host providers require ENV=local")
        from host_development import local_providers

        local_providers(Stack("local"), stop=command == "providers-stop")
    elif command == "test-providers":
        from host_development import test_providers

        test_providers()
    elif command in {"unit", "integration", "test", "coverage", "tooling"}:
        tests(command)
    elif command == "check":
        check()
    elif command == "smoke":
        from smoke.runtime import smoke

        smoke()
    elif command == "certify":
        from validation.certify_workflows import certify

        certify()
    elif command == "certify-host":
        from validation.certify_host import certify_host

        certify_host()
    elif command in {"build", "migrate", "run", "stop", "logs", "migration", "migration-check"}:
        if command == "migration" and (
            args.env != "local" or not os.environ.get("MESSAGE", "").strip()
        ):
            raise RuntimeError('Migration creation requires ENV=local and nonempty MESSAGE="..."')
        stack = Stack(args.env)
        if command == "build":
            stack.compose("build", "app")
        elif command == "migrate":
            stack.migrate()
        elif command == "run":
            stack.start()
            print(f"{args.env.upper()} ready: {stack.url}/swagger")
        elif command == "stop":
            stack.stop()
        elif command == "logs":
            stack.compose("logs", "--tail", "100")
        elif command == "migration-check":
            stack.providers()
            stack.command("alembic", "check")
        else:
            stack.providers()
            stack.command(
                "alembic",
                "revision",
                "--autogenerate",
                "-m",
                os.environ["MESSAGE"],
                options=(
                    "--user",
                    f"{os.getuid()}:{os.getgid()}",
                    "-v",
                    f"{ROOT / 'alembic'}:/app/alembic",
                ),
            )
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Workflow failed: {exc}", file=sys.stderr)
        sys.exit(exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1)
