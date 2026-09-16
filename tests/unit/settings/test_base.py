import pytest

from settings.base import ConfigurationError, Settings, boolean, database_url

URL = "postgresql://service:private_password@localhost/goalstats_test_config"


def test_explicit_settings_ignore_developer_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///developer.db")
    monkeypatch.setenv("OPENAPI_ENABLED", "invalid")
    result = Settings.load({"DATABASE_URL": URL})
    assert result.app_env == "local"
    assert result.openapi_enabled is False
    assert result.database_url.drivername == "postgresql+psycopg"
    assert "private_password" not in repr(result)


def test_environment_is_used_only_when_no_mapping_is_supplied(monkeypatch):
    monkeypatch.setenv("APP_ENV", "DEV")
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LOG_LEVEL", "warning")
    monkeypatch.setenv("OPENAPI_ENABLED", "true")
    settings = Settings.load()
    assert (settings.app_env, settings.log_level, settings.openapi_enabled) == (
        "dev",
        "WARNING",
        True,
    )
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        Settings.load({})


@pytest.mark.parametrize("env", ["local", "dev", "test"])
def test_supported_environments(env):
    assert Settings.load({"APP_ENV": env, "DATABASE_URL": URL}).app_env == env


@pytest.mark.parametrize(
    "value, expected", [("true", True), ("false", False), ("1", True), ("0", False)]
)
def test_boolean_contract(value, expected):
    assert boolean(value) is expected


@pytest.mark.parametrize(
    "key,value", [("APP_ENV", "prod"), ("LOG_LEVEL", "verbose"), ("OPENAPI_ENABLED", "yes")]
)
def test_invalid_settings_fail_with_safe_field_name(key, value):
    with pytest.raises(ConfigurationError, match=key):
        Settings.load({"DATABASE_URL": URL, key: value})


@pytest.mark.parametrize(
    "url",
    [
        "",
        "secret",
        "sqlite:///secret.db",
        "postgresql+asyncpg://user:secret@host/db",
        "postgresql://user:secret@host",
        "postgresql://user:secret@host:abc/db",
        "postgresql://user:secret@host:65536/db",
        "postgresql://user:secret@host/db?connect_timeout=999",
    ],
)
def test_invalid_database_urls_never_echo_values(url):
    with pytest.raises(ConfigurationError) as error:
        database_url(url)
    assert "secret" not in str(error.value)
    assert "DATABASE_URL" in str(error.value)


def test_encoded_password_and_explicit_driver_are_preserved():
    result = database_url("postgresql+psycopg://u:p%40ss%25@localhost:5432/goalstats_test_url")
    assert result.password == "p@ss%"
    assert result.port == 5432
