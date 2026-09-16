import pytest


@pytest.fixture
def explicit_config() -> dict[str, str]:
    return {
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql+psycopg://goalstats_test:unused@127.0.0.1:1/goalstats_test_absent",
        "OPENAPI_ENABLED": "true",
    }
