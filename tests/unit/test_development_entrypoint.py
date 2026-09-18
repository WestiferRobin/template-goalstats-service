"""Direct-only configuration, diagnostics, and single-process execution."""

import importlib
import os
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.exc import OperationalError

import main
from settings import host
from settings.base import ConfigurationError


@pytest.fixture
def host_file(tmp_path, monkeypatch):
    path = tmp_path / ".env.host.local"
    path.write_text(
        "APP_ENV=local\nDATABASE_URL=postgresql+psycopg://u:secret@127.0.0.1:55432/db\n"
        "REDIS_URL=redis://127.0.0.1:56379/0\n"
    )
    path.chmod(0o600)
    monkeypatch.setattr(host, "HOST_FILE", path)
    for key in host.KEYS:
        monkeypatch.delenv(key, raising=False)
    return path


@pytest.mark.parametrize("mode", [None, "local"])
def test_direct_local_constructs_once_without_reloader_or_dotenv(host_file, monkeypatch, mode):
    if mode is not None:
        monkeypatch.setenv("APP_ENV", mode)
    monkeypatch.setenv("FLASK_DEBUG", "1")
    before = dict(os.environ)
    factory = Mock()
    diagnostics = Mock()
    monkeypatch.setattr(main, "create_app", factory)
    monkeypatch.setattr(host, "diagnose_providers", diagnostics)
    monkeypatch.setattr(host, "check_app_port", Mock())
    main.development_main()
    factory.assert_called_once()
    values = factory.call_args.args[0]
    assert values["APP_ENV"] == "local" and values["FLASK_DEBUG"] == "0"
    assert values["DATABASE_URL"].endswith(":55432/db")
    diagnostics.assert_called_once_with(factory.return_value)
    factory.return_value.run.assert_called_once_with(
        host="127.0.0.1",
        port=5300,
        debug=False,
        use_debugger=False,
        use_reloader=False,
        load_dotenv=False,
    )
    assert dict(os.environ) == before


@pytest.mark.parametrize("mode", ["dev", "test", "production", "", " "])
def test_direct_refuses_nonlocal_before_reading_file(host_file, monkeypatch, mode):
    read = Mock(side_effect=AssertionError("must not read"))
    monkeypatch.setattr(host, "read_host_file", read)
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        host.load_host_config({"APP_ENV": mode})
    read.assert_not_called()


@pytest.mark.parametrize("cwd", ["root", "src"])
def test_file_location_does_not_depend_on_cwd(host_file, tmp_path, monkeypatch, cwd):
    directory = tmp_path / cwd
    directory.mkdir()
    (directory / ".env.host.local").write_text("must not load cwd file")
    monkeypatch.chdir(directory)
    assert host.load_host_config({})["APP_ENV"] == "local"


def test_missing_file_is_actionable(host_file):
    host_file.unlink()
    with pytest.raises(ConfigurationError, match="Run make providers ENV=local"):
        host.load_host_config({})


@pytest.mark.parametrize(
    "content",
    [
        "APP_ENV=local\nBROKEN",
        "APP_ENV=local\nAPP_ENV=local",
        "APP_ENV=local\nUNKNOWN=secret",
        "APP_ENV=dev",
        "APP_ENV=test",
        "APP_ENV=",
        "DATABASE_URL=secret",
        "APP_ENV=local\nLOG_LEVEL=I\x00NFO",
    ],
)
def test_bad_host_file_refused_without_values(host_file, content):
    host_file.write_text(content)
    with pytest.raises(ConfigurationError) as exc:
        host.load_host_config({"APP_ENV": "local"})
    assert "secret" not in str(exc.value)


def test_file_symlink_and_permissions_refused(host_file, tmp_path, monkeypatch):
    link = tmp_path / "link"
    link.symlink_to(host_file)
    with pytest.raises(ConfigurationError, match="symlinks"):
        host.read_host_file(link)
    host_file.chmod(0o644)
    with pytest.raises(ConfigurationError, match="private"):
        host.read_host_file(host_file)
    host_file.chmod(0o600)
    monkeypatch.setattr(host.os, "getuid", lambda: host_file.stat().st_uid + 1)
    with pytest.raises(ConfigurationError, match="owned"):
        host.read_host_file(host_file)


def test_nonregular_file_refused(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo, 0o600)
    with pytest.raises(ConfigurationError, match="regular"):
        host.read_host_file(fifo)


def test_literal_values_are_not_evaluated_or_interpolated(host_file):
    with host_file.open("a") as stream:
        stream.write("CACHE_KEY_PREFIX=${HOME}\n")
    assert host.read_host_file(host_file)["CACHE_KEY_PREFIX"] == "${HOME}"
    with pytest.raises(ConfigurationError, match="CACHE_KEY_PREFIX"):
        host.load_host_config({})


def test_precedence_defaults_and_optional_redis(host_file):
    with host_file.open("a") as stream:
        stream.write("HOST_APP_PORT=5400\nLOG_LEVEL=WARNING\n")
    config = host.load_host_config({"HOST_APP_PORT": "5500", "REDIS_URL": "", "LOG_LEVEL": "DEBUG"})
    assert config["HOST_APP_PORT"] == "5500"
    assert config["OPENAPI_ENABLED"] == "true"
    assert config["LOG_LEVEL"] == "DEBUG"
    assert config["REDIS_URL"] == ""
    assert "CACHE_KEY_PREFIX" not in config  # Existing Settings owns identity/defaults.


@pytest.mark.parametrize(
    "key,value",
    [
        ("DATABASE_URL", ""),
        ("DATABASE_URL", "secret"),
        ("DATABASE_URL", "postgresql://u:secret@remote/db"),
        ("REDIS_URL", "secret"),
        ("REDIS_URL", "redis://remote/0"),
        ("CACHE_KEY_PREFIX", "?"),
        ("CACHE_TTL_SECONDS", "0"),
        ("OPENAPI_ENABLED", "maybe"),
        ("LOG_LEVEL", "secret"),
        *[("HOST_APP_PORT", v) for v in ("0", "65536", "-1", "", "５３００", "abc")],
    ],
)
def test_invalid_override_refused(host_file, key, value):
    with pytest.raises(ConfigurationError) as exc:
        host.load_host_config({key: value})
    assert "secret" not in str(exc.value)


def test_missing_database_refused(host_file):
    host_file.write_text("APP_ENV=local\n")
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        host.load_host_config({})


def test_occupied_app_port_is_actionable(monkeypatch):
    socket = MagicMock()
    socket.return_value.__enter__.return_value.bind.side_effect = OSError("occupied")
    monkeypatch.setattr(host.socket, "socket", socket)
    with pytest.raises(ConfigurationError, match="choose HOST_APP_PORT"):
        host.check_app_port(5300)


@pytest.fixture
def diagnostic_app():
    db, cache, settings = Mock(), Mock(), Mock(cache_key_prefix="unit")
    app = Mock(
        extensions={
            "goalstats_database": db,
            "goalstats_cache": cache,
            "goalstats_settings": settings,
        }
    )
    return app, db, cache


def test_postgres_unavailable_is_redacted(diagnostic_app):
    app, db, _ = diagnostic_app
    db.engine.connect.side_effect = OperationalError("secret", {}, Exception("password"))
    with pytest.raises(ConfigurationError, match="LOCAL PostgreSQL is unavailable") as exc:
        host.diagnose_providers(app)
    assert "secret" not in str(exc.value) and "password" not in str(exc.value)
    db.dispose.assert_called_once()


def test_unmigrated_database_and_redis_outage_only_warn(diagnostic_app, monkeypatch):
    app, db, cache = diagnostic_app
    db.engine.connect.return_value.__enter__ = Mock()
    db.engine.connect.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(host, "is_ready", lambda _: False)
    cache.ready.return_value = False
    host.diagnose_providers(app)
    messages = [call.args[0] for call in app.logger.warning.call_args_list]
    assert any("make migrate ENV=local" in m for m in messages)
    assert any("database fallback" in m for m in messages)


def test_import_and_factory_never_read_host_file(monkeypatch):
    reader = Mock(side_effect=AssertionError("host file accessed"))
    monkeypatch.setattr(host, "read_host_file", reader)
    importlib.reload(main)
    before = dict(os.environ)
    app = main.create_app({"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@localhost/unit"})
    app.extensions["goalstats_database"].dispose()
    reader.assert_not_called()
    assert dict(os.environ) == before
