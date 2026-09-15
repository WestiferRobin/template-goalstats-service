import os
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from redis import Redis
from sqlalchemy import text

from goalstats_template import create_app
from goalstats_template.config import Settings, database_url
from goalstats_template.infrastructure.database.session import Database


@pytest.fixture
def explicit_config() -> dict[str, str]:
    return {
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql+psycopg://goalstats_test:unused@127.0.0.1:1/goalstats_test_absent",
        "OPENAPI_ENABLED": "true",
    }


@pytest.fixture
def app_factory() -> Iterator[Callable[[Mapping[str, str]], Flask]]:
    apps = []

    def make(config: Mapping[str, str]) -> Flask:
        app = create_app(config)
        apps.append(app)
        return app

    yield make
    for app in apps:
        app.extensions["goalstats_cache"].close()
        app.extensions["goalstats_database"].dispose()


@pytest.fixture
def app(app_factory, explicit_config) -> Flask:
    return app_factory(explicit_config)


@pytest.fixture(scope="session")
def postgres_config() -> dict[str, str]:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is not set; provision an isolated PostgreSQL test database.")
    if os.environ.get("TEST_DATABASE_DISPOSABLE") != "1":
        pytest.fail("TEST_DATABASE_DISPOSABLE=1 is required for provider tests.")
    try:
        url = database_url(value)
    except ValueError:
        pytest.fail("TEST_DATABASE_URL is invalid; its value is intentionally omitted.")
    if not url.database or not url.database.startswith("goalstats_test_"):
        pytest.fail("Provider tests require a dedicated goalstats_test_* database.")
    config = {"APP_ENV": "test", "DATABASE_URL": value, "OPENAPI_ENABLED": "true"}
    db = Database(Settings.load(config))
    try:
        with db.engine.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == url.database
        migration = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with db.engine.begin() as connection:
            migration.attributes["connection"] = connection
            command.upgrade(migration, "head")
    except Exception:
        pytest.fail(
            "Explicit TEST PostgreSQL is unavailable; refusing to fall back or skip.", pytrace=False
        )
    finally:
        db.dispose()
    return config


@pytest.fixture
def postgres_app(app_factory, postgres_config) -> Iterator[Flask]:
    app = app_factory(postgres_config)
    db = app.extensions["goalstats_database"]
    # Explicitly disposable database only; no shared developer rows.
    with db.engine.begin() as connection:
        connection.execute(text("DELETE FROM actions"))
        connection.execute(text("DELETE FROM items"))
    try:
        yield app
    finally:
        with db.engine.begin() as connection:
            connection.execute(text("DELETE FROM actions"))
            connection.execute(text("DELETE FROM items"))


@pytest.fixture
def probe_table(postgres_app) -> Iterator[str]:
    # A test-only table with no application model or migration. No existing tables are touched.
    name = "foundation_probe_" + uuid4().hex
    database = postgres_app.extensions["goalstats_database"]
    with database.engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE {name} (value integer NOT NULL)"))
    try:
        yield name
    finally:
        with database.engine.begin() as connection:
            connection.execute(text(f"DROP TABLE {name}"))


@pytest.fixture(scope="session")
def redis_url():
    value = os.environ.get("TEST_REDIS_URL")
    if not value:
        pytest.skip("TEST_REDIS_URL is not set; provision isolated Redis.")
    if os.environ.get("TEST_REDIS_DISPOSABLE") != "1":
        pytest.fail("TEST_REDIS_DISPOSABLE=1 is required.")
    from goalstats_template.config import redis_url as validate

    try:
        validate(value)
        client = Redis.from_url(value, socket_connect_timeout=1, socket_timeout=1)
        try:
            assert client.ping()
        finally:
            client.close()
    except Exception:
        pytest.fail("Explicit TEST Redis unavailable or invalid; refusing fallback.", pytrace=False)
    return value


@pytest.fixture
def redis_app(postgres_app, app_factory, postgres_config, redis_url):
    prefix = "goalstats_test_" + uuid4().hex
    app = app_factory({**postgres_config, "REDIS_URL": redis_url, "CACHE_KEY_PREFIX": prefix})
    try:
        yield app
    finally:
        client = app.extensions["goalstats_cache"].client
        keys = list(client.scan_iter(match=prefix + ":*"))
        if keys:
            client.delete(*keys)
        assert list(client.scan_iter(match=prefix + ":*")) == []
