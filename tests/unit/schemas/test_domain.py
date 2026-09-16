from uuid import UUID, uuid4

import pytest
from marshmallow import ValidationError

from enums.action import ActionType
from enums.item import ItemStatus
from schemas.action.request import (
    CreateActionSchema,
    NestedActionSchema,
    UpdateActionSchema,
)
from schemas.item.request import CreateItemSchema, UpdateItemSchema
from settings.base import ConfigurationError, Settings


@pytest.mark.parametrize(
    "schema,body",
    [
        (CreateItemSchema, {}),
        (CreateItemSchema, {"name": None}),
        (CreateItemSchema, {"name": ""}),
        (CreateItemSchema, {"name": " \t\n"}),
        (CreateItemSchema, {"name": "x" * 201}),
        (CreateItemSchema, {"name": 12}),
        (CreateItemSchema, {"name": "x", "extra": 1}),
        (UpdateItemSchema, {"name": "x"}),
        (UpdateItemSchema, {"name": "x", "status": "0"}),
        (UpdateItemSchema, {"name": "x", "status": 0}),
        (UpdateItemSchema, {"name": "x", "status": "invalid"}),
        (CreateActionSchema, {"name": "x", "type": "create"}),
        (CreateActionSchema, {"name": "x", "type": "create", "itemId": "bad"}),
        (CreateActionSchema, {"name": "x", "type": "create", "itemId": str(UUID(int=0))}),
        (NestedActionSchema, {"name": "x", "type": "create", "itemId": str(uuid4())}),
        (UpdateActionSchema, {"name": "x", "type": "delete", "itemId": str(uuid4())}),
        (NestedActionSchema, {"name": "x", "type": "0"}),
        (NestedActionSchema, {"name": "x", "type": False}),
    ],
)
def test_request_contract_rejects_invalid_values(schema, body):
    with pytest.raises(ValidationError):
        schema().load(body)


def test_valid_schemas_return_typed_internal_values():
    identity = uuid4()
    data = CreateActionSchema().load({"itemId": str(identity), "name": "x" * 200, "type": "update"})
    assert data == {"item_id": identity, "name": "x" * 200, "action_type": ActionType.UPDATE}
    assert (
        UpdateItemSchema().load({"name": "example", "status": "archived"})["status"]
        is ItemStatus.ARCHIVED
    )
    assert [x.value for x in ItemStatus] == ["active", "archived"]
    assert [x.value for x in ActionType] == ["create", "update", "delete"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("REDIS_URL", "http://private@host/0"),
        ("REDIS_URL", "redis://host/abc"),
        ("REDIS_URL", "redis://host/0?socket_timeout=999"),
        ("REDIS_URL", "redis://host:99999/0"),
        ("CACHE_KEY_PREFIX", "bad prefix"),
        ("CACHE_KEY_PREFIX", ""),
        ("CACHE_TTL_SECONDS", "0"),
        ("CACHE_TTL_SECONDS", "x"),
        ("CACHE_TTL_SECONDS", "86401"),
    ],
)
def test_cache_settings_fail_safely(explicit_config, key, value):
    with pytest.raises(ConfigurationError) as error:
        Settings.load({**explicit_config, key: value})
    assert key in str(error.value)
    assert "private" not in str(error.value)


def test_cache_settings_defaults_and_explicit_isolation(explicit_config, monkeypatch):
    monkeypatch.setenv("REDIS_URL", "invalid")
    settings = Settings.load(explicit_config)
    assert settings.redis_url is None
    assert settings.cache_key_prefix == "goalstats-template-py:test:v1"
    assert settings.cache_ttl_seconds == 300
    settings = Settings.load({**explicit_config, "REDIS_URL": "redis://:private@localhost/0"})
    assert "private" not in repr(settings)
