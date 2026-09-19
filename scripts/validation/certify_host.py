"""Automated host acceptance using disposable resources, never developer LOCAL data.

Run with the freshly installed repository .venv Python 3.12 and PYTHONPATH=scripts.
Actual PyCharm/VS Code UI breakpoint acceptance remains a separate manual check.
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

from environment_config import schema
from environment_setup import text as env_text
from host_development import local_environment, local_providers, private_write
from http_client import request
from test_ownership import verify_host_session
from workflow import ROOT, assert_absent, fresh, install_signals, inventory, run, wait_ready


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return str(sock.getsockname()[1])


def stop_child(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=45)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            raise AssertionError("Owner did not terminate cleanly") from None


def clean_env():
    return {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(
            ("TEST_", "DATABASE_", "REDIS_", "APP_", "FLASK_", "CACHE_", "COMPOSE_", "HOST_")
        )
        and k not in {"LOG_LEVEL", "OPENAPI_ENABLED", "PYTHONPATH"}
    }


def certify_session(signum):
    sessions = ROOT / ".host-sessions"
    before = set(sessions.glob("*/manifest.json"))
    with tempfile.TemporaryDirectory() as directory:
        log_path = Path(directory) / "owner.log"
        with log_path.open("w") as output:
            child = subprocess.Popen(
                [sys.executable, "-u", "scripts/workflow.py", "test-providers"],
                cwd=ROOT,
                env=clean_env(),
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            project = None
            try:
                deadline = time.monotonic() + 120
                while "Owned TEST session ready." not in log_path.read_text():
                    if child.poll() is not None or time.monotonic() > deadline:
                        raise AssertionError("TEST owner failed: " + log_path.read_text())
                    time.sleep(0.2)
                paths = set(sessions.glob("*/manifest.json")) - before
                assert len(paths) == 1
                path = paths.pop()
                env = {
                    **clean_env(),
                    **json.loads(path.read_text())["urls"],
                    "TEST_SESSION_MANIFEST": str(path),
                    "TEST_DATABASE_DISPOSABLE": "1",
                    "TEST_REDIS_DISPOSABLE": "1",
                }
                manifest = verify_host_session(env)
                project = manifest["project"]
                assert path.stat().st_mode & 0o777 == 0o600
                if signum == signal.SIGTERM:
                    run(
                        [
                            sys.executable,
                            "-m",
                            "pytest",
                            "-q",
                            "tests/integration/infra/repositories/test_persistence.py::"
                            "test_repositories_flush_without_committing_and_lists_are_deterministic",
                            "tests/integration/migrations/test_schema.py",
                            "tests/integration/infra/caches/test_redis.py",
                        ],
                        env=clean_env(),
                    )
                for key in ("TEST_DATABASE_URL", "TEST_REDIS_URL"):
                    bad = {**env, key: env[key] + "wrong"}
                    try:
                        verify_host_session(bad)
                    except RuntimeError:
                        pass
                    else:
                        raise AssertionError("Mismatched endpoint accepted")
                child.send_signal(signum)
                assert child.wait(timeout=60) == 128 + signum
                assert not path.exists()
                assert not path.parent.exists()
                try:
                    verify_host_session(env)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Stale session accepted")
                assert_absent(project)
            finally:
                stop_child(child)
                if project:
                    assert_absent(project)
    print(f"Owned TEST session, mismatch/stale refusal, signal {signum}: PASS", flush=True)


def certify_host():
    # The real repository's private host file is never overwritten for certification.
    # Exercise the actual fixed repo-relative path in an exact disposable source copy.
    with tempfile.TemporaryDirectory(prefix="host-entrypoint-") as directory:
        root = Path(directory)
        names = run(["git", "ls-files", "-co", "--exclude-standard", "-z"], capture=True).stdout
        for name in set(filter(None, names.split("\0"))):
            source = ROOT / name
            if source.is_file():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        (root / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
        run(
            [sys.executable, str(root / "scripts/validation/certify_host.py")],
            env={**clean_env(), "PYTHONPATH": str(root / "scripts")},
        )


def certify_isolated_host():
    assert sys.version_info[:2] == (3, 12), "Host certification requires Python 3.12"
    assert Path(sys.prefix).resolve() == (ROOT / ".venv").resolve(), "Use repository .venv"
    run([sys.executable, "-m", "pip", "check"])
    for args in (
        ["tests/unit"],
        ["tests/unit/settings"],
        ["tests/unit/test_development_entrypoint.py"],
        ["tests/unit/exceptions/test_base.py::test_validation_error_has_safe_stable_contract"],
        ["--collect-only", "tests"],
    ):
        result = run([sys.executable, "-m", "pytest", "-q", *args], env=clean_env(), capture=True)
        assert " skipped" not in result.stdout
        assert "tests/smoke/" not in result.stdout
        print(result.stdout.splitlines()[-1], flush=True)
    for name in ("settings.json", "launch.json", "extensions.json"):
        data = (ROOT / ".vscode" / name).read_text()
        json.loads(data)
        assert str(ROOT) not in data and ".host-sessions/" not in data
    baseline = inventory()
    from validation.certify_environment import certify_environment

    certify_environment()
    stack = fresh("local")
    for key in ("LOCAL_POSTGRES_PORT", "LOCAL_REDIS_PORT", "HOST_APP_PORT"):
        stack.settings[key] = free_port()
        stack.process_env[key] = stack.settings[key]
    child = None
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = ROOT / ".env.local"
            missing = run(
                [sys.executable, "src/main.py"], env=clean_env(), capture=True, check=False
            )
            assert missing.returncode and "LOCAL configuration is missing" in missing.stderr
            assert "Traceback" not in missing.stderr
            machine_values = schema.machine(
                {
                    "POSTGRES_PASSWORD": stack.settings["POSTGRES_PASSWORD"],
                    "DEV_POSTGRES_PASSWORD": "unused_certificate_password",
                    "LOCAL_APP_PORT": stack.settings["APP_PORT"],
                    **{
                        k: stack.settings[k]
                        for k in ("HOST_APP_PORT", "LOCAL_POSTGRES_PORT", "LOCAL_REDIS_PORT")
                    },
                }
            )
            private_write(path, env_text(machine_values))
            local_providers(stack)
            before = path.read_bytes()
            local_providers(stack)
            assert path.read_bytes() == before and path.stat().st_mode & 0o777 == 0o600
            assert not stack.compose("ps", "-q", "app", capture=True).stdout.strip()
            # Recreating a container with changed config must not pretend to rotate
            # the password stored in its existing disposable certification volume.
            password = stack.settings["POSTGRES_PASSWORD"]
            stack.compose("stop", "postgres")
            stack.compose("rm", "-f", "postgres")
            stack.settings["POSTGRES_PASSWORD"] = "deliberately_wrong_password"
            stack.process_env["POSTGRES_PASSWORD"] = "deliberately_wrong_password"
            try:
                local_providers(stack)
            except RuntimeError as exc:
                assert "authentication failed" in str(exc)
            else:
                raise AssertionError(
                    "Changed config falsely accepted as rotated volume credentials"
                )
            finally:
                stack.settings["POSTGRES_PASSWORD"] = password
                stack.process_env["POSTGRES_PASSWORD"] = password
                stack.compose("stop", "postgres")
                stack.compose("rm", "-f", "postgres")
            local_providers(stack)
            env = {**clean_env(), **local_environment(stack)}
            from redis import Redis
            from sqlalchemy import create_engine, text

            engine = create_engine(env["DATABASE_URL"])
            try:
                with engine.connect() as connection:
                    assert connection.scalar(text("SELECT 1")) == 1
            finally:
                engine.dispose()
            cache = Redis.from_url(env["REDIS_URL"])
            try:
                assert cache.ping()
            finally:
                cache.close()
            for mode in ("dev", "test", "", "unknown"):
                refused = run(
                    [sys.executable, "src/main.py"],
                    env={**clean_env(), "APP_ENV": mode},
                    capture=True,
                    check=False,
                )
                assert refused.returncode and "conflicting APP_ENV" in refused.stderr
                assert "Traceback" not in refused.stderr
            url = "http://127.0.0.1:" + env["HOST_APP_PORT"]
            with socket.socket() as occupied:
                occupied.bind(("127.0.0.1", int(env["HOST_APP_PORT"])))
                occupied.listen()
                refused = run(
                    [sys.executable, "src/main.py"],
                    env=clean_env(),
                    capture=True,
                    check=False,
                )
                assert refused.returncode and "choose HOST_APP_PORT" in refused.stderr
            # Reachable, unmigrated PostgreSQL must not prevent direct startup.
            with (Path(directory) / "unmigrated.log").open("w") as output:
                child = subprocess.Popen(
                    [sys.executable, "src/main.py"],
                    cwd=ROOT,
                    env=clean_env(),
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
                deadline = time.monotonic() + 30
                while True:
                    try:
                        assert request(url, "/health")[0] == "Healthy"
                        break
                    except (urllib.error.URLError, ConnectionError):
                        assert child.poll() is None and time.monotonic() < deadline
                        time.sleep(0.1)
                assert request(url, "/ready", expected=503)[0] == "Unhealthy"
                stop_child(child)
                child = None
            assert "make migrate ENV=local" in (Path(directory) / "unmigrated.log").read_text()
            stack.compose("build", "app")
            stack.migrate()
            stack.command("alembic", "check")
            url = "http://127.0.0.1:" + env["HOST_APP_PORT"]
            log = Path(directory) / "app.log"
            with log.open("w") as output:
                child = subprocess.Popen(
                    [sys.executable, "src/main.py"],
                    cwd=ROOT,
                    env=clean_env(),
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
                wait_ready(url)
                assert request(url, "/health")[0] == "Healthy"
                item, _ = request(url, "/items", "POST", {"name": "host persistence"}, 201)
                item_path = "/items/" + item["id"]
                assert request(url, item_path)[0] == item
                updated, _ = request(
                    url, item_path, "PUT", {"name": "host updated", "status": "active"}
                )
                # No child/reloader/debugger process belongs to this application.
                children = subprocess.run(["pgrep", "-P", str(child.pid)], capture_output=True)
                assert children.returncode == 1 and not children.stdout
                stop_child(child)
                child = None
                local_providers(stack, stop=True)
                refused = run(
                    [sys.executable, "src/main.py"],
                    env=clean_env(),
                    capture=True,
                    check=False,
                )
                assert refused.returncode and "LOCAL PostgreSQL is unavailable" in refused.stderr
                assert "Traceback" not in refused.stderr and password not in refused.stderr
                local_providers(stack)
                stack.compose("stop", "redis")
                child = subprocess.Popen(
                    [sys.executable, "main.py"],
                    cwd=ROOT / "src",
                    env=clean_env(),
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
                deadline = time.monotonic() + 30
                while True:
                    try:
                        assert request(url, "/ready")[0] == "Degraded"
                        break
                    except (urllib.error.URLError, ConnectionError):
                        assert child.poll() is None and time.monotonic() < deadline
                        time.sleep(0.1)
                assert request(url, item_path)[0] == updated
                request(url, item_path, "DELETE", expected=204)
                request(url, item_path, expected=404)
                stop_child(child)
                child = None
            assert "Restarting with" not in log.read_text()
            assert "Debugger is active" not in log.read_text()
            stack.start()
            for stop in (False, True):
                try:
                    local_providers(stack, stop=stop)
                except RuntimeError as exc:
                    assert "active" in str(exc)
                else:
                    raise AssertionError("Active full LOCAL app was not protected")
            stack.compose("stop", "app")
            local_providers(stack, stop=True)
            for sig in (signal.SIGTERM, signal.SIGINT):
                certify_session(sig)
    finally:
        if child:
            stop_child(child)
        stack.stop(volumes=True)
        assert_absent(stack.project)
    after = inventory()
    for kind in baseline:
        assert baseline[kind] <= after[kind], f"Unrelated {kind} removed"
        if kind != "images":
            assert baseline[kind] == after[kind], f"Leaked {kind}"
    print("Host certification: PASS; READY FOR MANUAL IDE VERIFICATION", flush=True)


if __name__ == "__main__":
    install_signals()
    certify_isolated_host()
