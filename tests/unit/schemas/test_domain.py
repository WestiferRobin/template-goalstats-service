from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from enums.action import ActionType
from enums.item import ItemStatus
from schemas.action import ActionCreate, ActionWrite
from schemas.item import ItemCreate, ItemUpdate


@pytest.mark.parametrize(
    "schema,body",
    [
        (ItemCreate, {}),
        (ItemCreate, {"name": None}),
        (ItemCreate, {"name": ""}),
        (ItemCreate, {"name": " \t\n"}),
        (ItemCreate, {"name": "x" * 201}),
        (ItemCreate, {"name": 12}),
        (ItemCreate, {"name": "x", "extra": 1}),
        (ItemUpdate, {"name": "x"}),
        (ItemUpdate, {"name": "x", "status": "0"}),
        (ItemUpdate, {"name": "x", "status": 0}),
        (ItemUpdate, {"name": "x", "status": "invalid"}),
        (ActionCreate, {"name": "x", "type": "create"}),
        (ActionCreate, {"name": "x", "type": "create", "itemId": "bad"}),
        (ActionCreate, {"name": "x", "type": "create", "itemId": str(UUID(int=0))}),
        (ActionWrite, {"name": "x", "type": "create", "itemId": str(uuid4())}),
        (ActionWrite, {"name": "x", "type": "delete", "itemId": str(uuid4())}),
        (ActionWrite, {"name": "x", "type": "0"}),
        (ActionWrite, {"name": "x", "type": False}),
    ],
)
def test_request_contract_rejects_invalid_values(schema, body):
    with pytest.raises(ValidationError):
        schema.model_validate(body)


def test_valid_schemas_return_typed_internal_values():
    identity = uuid4()
    data = ActionCreate.model_validate(
        {"itemId": str(identity), "name": "x" * 200, "type": "update"}
    )
    assert data.model_dump() == {
        "item_id": identity,
        "name": "x" * 200,
        "action_type": ActionType.UPDATE,
    }
    assert (
        ItemUpdate.model_validate({"name": "example", "status": "archived"}).status
        is ItemStatus.ARCHIVED
    )
    assert [x.value for x in ItemStatus] == ["active", "archived"]
    assert [x.value for x in ActionType] == ["create", "update", "delete"]


def test_responses_are_detached_frozen_and_preserve_wire_timestamps():
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from schemas.action import ActionResponse
    from schemas.item import ItemListResponse, ItemResponse

    now = datetime(2026, 1, 1, tzinfo=UTC)
    identity = UUID(int=1)
    row = SimpleNamespace(
        id=identity, name=" x ", status=ItemStatus.ACTIVE, created_at=now, updated_at=now
    )
    result = ItemResponse.model_validate(row, by_name=True, by_alias=False)
    expected = {
        "id": str(identity),
        "name": " x ",
        "status": "active",
        "createdAt": "2026-01-01T00:00:00+00:00",
        "updatedAt": "2026-01-01T00:00:00+00:00",
    }
    assert result.model_dump(mode="json", by_alias=True) == expected
    assert ItemListResponse([result]).model_dump(mode="json", by_alias=True) == [expected]
    with pytest.raises(ValidationError):
        result.name = "changed"
    with pytest.raises(ValidationError):
        ItemResponse.model_validate({**expected, "createdAt": "2026-01-01T00:00:00"})
    # Action's payload contains no Item status and retains public aliases.
    payload = {k: v for k, v in expected.items() if k != "status"}
    payload.update(itemId=str(identity), type="create")
    action = ActionResponse.model_validate(payload)
    assert action.model_dump(mode="json", by_alias=True) == payload


@pytest.mark.parametrize(
    "body",
    [
        {"item_id": str(UUID(int=1)), "name": "x", "type": "create"},
        {"itemId": str(UUID(int=1)), "name": "x", "action_type": "create"},
    ],
)
def test_http_contracts_never_accept_internal_aliases(body):
    with pytest.raises(ValidationError):
        ActionCreate.model_validate(body)
