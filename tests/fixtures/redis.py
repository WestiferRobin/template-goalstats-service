import os
from uuid import uuid4

import pytest
from redis import Redis


@pytest.fixture(scope="session")
def redis_url():
    value = os.environ.get("TEST_REDIS_URL")
    if not value:
        pytest.skip("TEST_REDIS_URL is not set; provision isolated Redis.")
    if os.environ.get("TEST_REDIS_DISPOSABLE") != "1":
        pytest.fail("TEST_REDIS_DISPOSABLE=1 is required.")
    from settings.base import redis_url as validate

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
