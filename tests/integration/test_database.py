import pytest
from sqlalchemy import text
from sqlalchemy.exc import InvalidRequestError

from goalstats_template.dependencies import get_session

pytestmark = pytest.mark.postgres


def test_ready_uses_real_postgresql_and_releases_connection(postgres_app):
    response = postgres_app.test_client().get("/ready")
    assert (response.status_code, response.text) == (200, "Degraded")
    assert postgres_app.extensions["goalstats_database"].engine.pool.checkedout() == 0


def test_real_postgresql_authentication_failure_is_safe(app_factory, postgres_config):
    from goalstats_template.config import database_url

    url = database_url(postgres_config["DATABASE_URL"]).set(
        password="intentionally_invalid_password"
    )
    app = app_factory(
        {**postgres_config, "DATABASE_URL": url.render_as_string(hide_password=False)}
    )
    assert app.test_client().get("/health").status_code == 200
    response = app.test_client().get("/ready")
    assert (response.status_code, response.text) == (503, "Unhealthy")


@pytest.mark.parametrize("fail", [False, True])
def test_request_teardown_rolls_back_uncommitted_work_and_closes_session(
    postgres_app, probe_table, fail
):
    sessions = []

    @postgres_app.get("/_session")
    def operation():
        session = get_session()
        assert get_session() is session
        sessions.append(session)
        session.execute(text(f"INSERT INTO {probe_table} VALUES (1)"))
        if fail:
            raise RuntimeError("private provider details")
        return "ok"

    client = postgres_app.test_client()
    for _ in range(2):
        assert client.get("/_session").status_code == (500 if fail else 200)
        assert postgres_app.extensions["goalstats_database"].engine.pool.checkedout() == 0
    assert sessions[0] is not sessions[1]
    for session in sessions:
        with pytest.raises(InvalidRequestError):
            session.execute(text("SELECT 1"))
    with postgres_app.extensions["goalstats_database"].engine.connect() as connection:
        assert connection.scalar(text(f"SELECT count(*) FROM {probe_table}")) == 0


def test_explicit_application_transactions_commit_or_roll_back(postgres_app, probe_table):
    database = postgres_app.extensions["goalstats_database"]
    with database.transaction() as session:
        session.execute(text(f"INSERT INTO {probe_table} VALUES (1)"))
    with pytest.raises(RuntimeError):
        with database.transaction() as session:
            session.execute(text(f"INSERT INTO {probe_table} VALUES (2)"))
            raise RuntimeError("abort operation")
    with database.engine.connect() as connection:
        assert connection.scalars(text(f"SELECT value FROM {probe_table}")).all() == [1]
    assert database.engine.pool.checkedout() == 0


def test_request_session_can_commit_at_explicit_operation_boundary(postgres_app, probe_table):
    @postgres_app.post("/_commit")
    def operation():
        with get_session().begin():
            get_session().execute(text(f"INSERT INTO {probe_table} VALUES (3)"))
        return "ok"

    assert postgres_app.test_client().post("/_commit").status_code == 200
    database = postgres_app.extensions["goalstats_database"]
    with database.engine.connect() as connection:
        assert connection.scalars(text(f"SELECT value FROM {probe_table}")).all() == [3]
    assert database.engine.pool.checkedout() == 0
