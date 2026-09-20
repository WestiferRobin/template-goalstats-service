from uuid import uuid4

import pytest
from redis import Redis
from test_ownership import owned_test_config


@pytest.fixture(scope="session")
def redis_url():
    try:
        owned = owned_test_config()
    except RuntimeError as exc:
        pytest.fail(str(exc), pytrace=False)
    value = owned.get("TEST_REDIS_URL")
    if not value or owned.get("TEST_REDIS_DISPOSABLE") != "1":
        pytest.fail("Verified disposable TEST configuration is required.", pytrace=False)
    from settings.redis import redis_url as validate

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
