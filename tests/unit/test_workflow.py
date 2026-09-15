"""Provider-free tests for destructive-workflow guards and configuration parsing."""

import pytest
from workflow import Stack, read_settings


@pytest.mark.parametrize("environment", ["production", "locla", "", "LOCAL"])
def test_unknown_environment_refused_before_configuration_or_docker(environment):
    with pytest.raises(RuntimeError, match="ENV must"):
        Stack(environment)


def test_persistent_stack_refuses_volume_deletion():
    stack = Stack("local", settings={"POSTGRES_PASSWORD": "not-used", "APP_PORT": "5100"})
    with pytest.raises(RuntimeError, match="persistent"):
        stack.stop(volumes=True)


@pytest.mark.parametrize("project", ["other-project", "goalstats-template-py-local", ""])
def test_disposable_stack_requires_owned_identity(project):
    with pytest.raises(RuntimeError, match="Disposable project"):
        Stack("test", project=project, settings={})


def test_environment_parser_preserves_values_without_shell_execution(tmp_path):
    config = tmp_path / ".env.local"
    config.write_text("# comment\nPOSTGRES_PASSWORD=abcdefghijklmnop\nAPP_PORT=5101\n")
    assert read_settings(config) == {"POSTGRES_PASSWORD": "abcdefghijklmnop", "APP_PORT": "5101"}
    config.write_text("POSTGRES_PASSWORD=$(touch unexpected)\nAPP_PORT=5101\n")
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        read_settings(config)
    assert not (tmp_path / "unexpected").exists()


def test_ambient_database_and_compose_settings_do_not_choose_test_resources(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "developer-database")
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "unrelated")
    stack = Stack(
        "test",
        project="goalstats-template-py-test-a123",
        settings={"POSTGRES_PASSWORD": "test-only"},
    )
    assert "unrelated" not in stack.args
    assert "COMPOSE_PROJECT_NAME" not in stack.process_env
    assert stack.service == "runner"
    assert stack.settings == {"POSTGRES_PASSWORD": "test-only"}
