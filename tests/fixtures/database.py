import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from sqlalchemy import text
from test_ownership import verify_test_providers

from infra.resources.db import Database
from settings.base import Settings, database_url


@pytest.fixture(scope="session")
def postgres_config() -> dict[str, str]:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is not set; provision an isolated PostgreSQL test database.")
    if os.environ.get("TEST_DATABASE_DISPOSABLE") != "1":
        pytest.fail("TEST_DATABASE_DISPOSABLE=1 is required for provider tests.")
    try:
        verify_test_providers()
    except RuntimeError as exc:
        pytest.fail(str(exc), pytrace=False)
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
        migration = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
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
