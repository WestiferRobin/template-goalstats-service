import pytest

from settings.base import ConfigurationError
from settings.database import database_url


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
