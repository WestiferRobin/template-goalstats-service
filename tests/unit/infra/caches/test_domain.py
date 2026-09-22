import logging
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from enums.action import ActionType
from enums.item import ItemStatus
from infra.caches.action import ActionCache
from infra.caches.item import ItemCache
from infra.resources.redis import RedisCache
from schemas.action.response import ActionResponse
from schemas.item.response import ItemResponse
from settings.environment import load_application


@pytest.mark.parametrize("kind", ["item", "action"])
def test_domain_cache_roundtrip_and_invalid_payloads(kind):
    backend = Mock(spec=RedisCache)
    cache = (ItemCache if kind == "item" else ActionCache)(backend, "service:test:v1", 300)
    now, identity = datetime.now(UTC), uuid4()
    result = (
        ItemResponse(id=identity, name="x", status=ItemStatus.ACTIVE, createdAt=now, updatedAt=now)
        if kind == "item"
        else ActionResponse(
            id=identity,
            itemId=uuid4(),
            name="x",
            type=ActionType.CREATE,
            createdAt=now,
            updatedAt=now,
        )
    )
    cache.set(result)
    key, data, ttl = backend.set.call_args.args
    assert key == f"service:test:v1:{kind}s:{identity}"
    assert ttl == 300
    backend.get.return_value = data
    assert cache.get(identity) == result
    for bad in [
        {},
        {**data, "id": str(uuid4())},
        {**data, "createdAt": "not-a-date"},
        {**data, "name": " "},
    ]:
        backend.get.return_value = bad
        assert cache.get(identity) is None
    assert backend.delete.call_count == 4


@pytest.mark.parametrize("payload", [b"{", b"[]", b"null", b"1", b"\xff"])
def test_generic_cache_treats_corrupt_data_as_miss(explicit_config, payload):
    cache = RedisCache(load_application(explicit_config).redis, Mock(spec=logging.Logger))
    cache.client = Mock()
    cache.client.get.return_value = payload
    assert cache.get("key") is None


def test_provider_failures_are_safe_and_optional(explicit_config):
    logger = Mock(spec=logging.Logger)
    cache = RedisCache(load_application(explicit_config).redis, logger)
    assert cache.get("x") is None
    assert cache.ready("x") is False
    cache.set("x", {}, 1)
    cache.delete("x")
    cache.client = Mock()
    for operation in [cache.client.get, cache.client.set, cache.client.delete]:
        operation.side_effect = RedisError("password=private")
    assert cache.get("x") is None
    cache.set("x", {}, 1)
    cache.delete("x")
    assert cache.ready("x") is False
    assert "private" not in str(logger.mock_calls)
