import os
import subprocess
import sys
from pathlib import Path

from composition import get_database


def test_factory_instances_have_independent_resources(app_factory, explicit_config):
    first = app_factory(explicit_config)
    second = app_factory({**explicit_config, "OPENAPI_ENABLED": "false", "LOG_LEVEL": "ERROR"})
    assert (
        first.extensions["goalstats_database"].engine
        is not second.extensions["goalstats_database"].engine
    )
    assert first.extensions["goalstats_api"] is not second.extensions["goalstats_api"]
    assert first.logger is not second.logger
    assert first.logger.level != second.logger.level
    with first.app_context():
        database = get_database()
        assert get_database() is database
        with second.app_context():
            assert get_database() is not database
        assert get_database() is database
    assert first.test_client().get("/swagger/v1/swagger.json").status_code == 200
    assert second.test_client().get("/swagger/v1/swagger.json").status_code == 404


def test_health_is_independent_of_unreachable_database(app):
    db = app.extensions["goalstats_database"]
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.text == "Healthy"
    assert response.mimetype == "text/plain"
    assert db.engine.pool.checkedout() == 0


def test_unavailable_database_is_unhealthy_without_provider_details(app):
    response = app.test_client().get("/ready")
    assert response.status_code == 503
    assert response.text == "Unhealthy"
    assert response.mimetype == "text/plain"
    assert app.extensions["goalstats_database"].engine.pool.checkedout() == 0


def test_openapi_preserves_problem_contract_and_excludes_operational_paths(app):
    spec = app.test_client().get("/swagger/v1/swagger.json").json
    assert spec["openapi"] == "3.0.3"
    assert "/health" not in spec["paths"] and "/ready" not in spec["paths"]
    assert "/items" in spec["paths"] and "/actions" in spec["paths"]
    assert set(spec["components"]["schemas"]["ProblemDetails"]["required"]) == {
        "type",
        "title",
        "status",
        "detail",
    }
    assert "application/problem+json" in spec["components"]["responses"]["Problem"]["content"]


def test_import_and_factory_have_no_filesystem_or_provider_side_effects(tmp_path):
    source = Path(__file__).resolve().parents[2] / "src"
    code = r"""
import os, sys

def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'os.mkdir', 'os.remove', 'os.rename'}:
        raise AssertionError('Unexpected side effect: ' + event)
    if event == 'open':
        mode, flags = args[1], args[2]
        writing_mode = isinstance(mode, str) and any(c in mode for c in 'wax+')
        writing_flags = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
        if writing_mode or writing_flags:
            raise AssertionError('Unexpected file write')
sys.addaudithook(audit)
from main import create_app
from models.base import Base
assert set(Base.metadata.tables) == {'items', 'actions'}
app = create_app({'APP_ENV': 'test', 'DATABASE_URL': 'postgresql://u:p@127.0.0.1:1/goalstats_test_import'})
assert app.test_client().get('/health').text == 'Healthy'
app.extensions['goalstats_database'].dispose()
"""
    env = {
        **os.environ,
        "PYTHONPATH": str(source),
        "PYTHONDONTWRITEBYTECODE": "1",
        "DATABASE_URL": "invalid",
    }
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []
