"""Migration is transactional with respect to validation and keeps both credentials."""

from unittest.mock import Mock

import pytest
from environment_config import schema
from environment_setup import private_write, setup_files


def legacy(root):
    private_write(root / ".env.local", "POSTGRES_PASSWORD=abcdefghijklmnop\nAPP_PORT=5101\n")
    private_write(root / ".env.dev", "POSTGRES_PASSWORD=ponmlkjihgfedcba\nAPP_PORT=5201\n")


def test_fresh_and_idempotent(tmp_path):
    setup_files(tmp_path, has_volume=lambda _: False, verify=Mock())
    assert {p.name for p in tmp_path.iterdir()} == {".env.local", ".env.test"}
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in tmp_path.iterdir())
    setup_files(tmp_path, has_volume=lambda _: False, verify=Mock())
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_migration_preserves_both_credentials_and_authenticates_before_retiring(tmp_path):
    legacy(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    calls = []

    def verify(mode, values):
        assert (tmp_path / ".env.dev").exists()
        calls.append(mode)
        assert values["POSTGRES_PASSWORD"] == "abcdefghijklmnop"
        assert values["DEV_POSTGRES_PASSWORD"] == "ponmlkjihgfedcba"

    setup_files(tmp_path, has_volume=lambda _: True, verify=verify)
    assert calls == ["local", "dev"]
    values = schema.load_machine(tmp_path / ".env.local")
    assert values["LOCAL_APP_PORT"] == "5101" and values["DEV_APP_PORT"] == "5201"
    assert not (tmp_path / ".env.dev").exists()
    backups = list((tmp_path / ".host-sessions").glob("migration-*"))
    assert len(backups) == 1
    for name, content in before.items():
        assert (backups[0] / (name + ".backup")).read_bytes() == content


@pytest.mark.parametrize("failure", ["auth", "host", "policy"])
def test_conflicts_leave_every_original_byte(tmp_path, failure):
    legacy(tmp_path)
    if failure == "host":
        private_write(tmp_path / ".env.host.local", "APP_ENV=dev\n")
    if failure == "policy":
        private_write(tmp_path / ".env.test", "DATABASE_URL=forbidden\n")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises((RuntimeError, schema.EnvironmentError)):
        setup_files(
            tmp_path, has_volume=lambda _: True, verify=Mock(side_effect=RuntimeError("auth"))
        )
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_missing_configuration_never_replaces_existing_volume_password(tmp_path):
    with pytest.raises(RuntimeError, match="Restore"):
        setup_files(tmp_path, has_volume=lambda _: True, verify=Mock())
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "key",
    [
        "DATABASE_URL",
        "REDIS_URL",
        "POSTGRES_PASSWORD",
        "APP_PORT",
        "TEST_DATABASE_DISPOSABLE",
        "TEST_SESSION_MANIFEST",
    ],
)
def test_test_policy_never_accepts_provider_authority(tmp_path, key):
    private_write(tmp_path / ".env.test", key + "=secret\n")
    with pytest.raises(schema.EnvironmentError) as error:
        schema.test_policy(tmp_path)
    assert "secret" not in str(error.value)


def test_host_and_container_urls_share_local_identity():
    values = schema.machine(
        {"POSTGRES_PASSWORD": "abcdefghijklmnop", "DEV_POSTGRES_PASSWORD": "ponmlkjihgfedcba"}
    )
    host = schema.application(values, "local", host=True)
    docker = schema.application(values, "local")
    assert (
        host["DATABASE_URL"].replace("127.0.0.1:55432", "postgres:5432") == docker["DATABASE_URL"]
    )
    assert host["REDIS_URL"].replace("127.0.0.1:56379", "redis:6379") == docker["REDIS_URL"]
    assert host["CACHE_KEY_PREFIX"] == docker["CACHE_KEY_PREFIX"]
