import pytest
from sqlalchemy import text
from sqlalchemy.exc import InvalidRequestError

pytestmark = pytest.mark.postgres


def test_ready_uses_real_postgresql_and_releases_connection(postgres_app):
    response = postgres_app.test_client().get("/ready")
    assert (response.status_code, response.text) == (200, "Degraded")
    assert postgres_app.extensions["goalstats_database"].engine.pool.checkedout() == 0


def test_real_postgresql_authentication_failure_is_safe(app_factory, postgres_config):
    from settings.database import database_url

    url = database_url(postgres_config["DATABASE_URL"]).set(
        password="intentionally_invalid_password"
    )
    app = app_factory(
        {**postgres_config, "DATABASE_URL": url.render_as_string(hide_password=False)}
    )
    assert app.test_client().get("/health").status_code == 200
    response = app.test_client().get("/ready")
    assert (response.status_code, response.text) == (503, "Unhealthy")


def test_explicit_application_transactions_commit_or_roll_back(postgres_app, probe_table):
    database = postgres_app.extensions["goalstats_database"]
    with database.transaction() as session:
        session.execute(text(f"INSERT INTO {probe_table} VALUES (1)"))
    with pytest.raises(RuntimeError):
        with database.transaction() as session:
            session.execute(text(f"INSERT INTO {probe_table} VALUES (2)"))
            raise RuntimeError("abort operation")
    with pytest.raises(InvalidRequestError):
        session.execute(text("SELECT 1"))
    with database.engine.connect() as connection:
        assert connection.scalars(text(f"SELECT value FROM {probe_table}")).all() == [1]
    assert database.engine.pool.checkedout() == 0
