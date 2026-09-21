from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from enums.action import ActionType
from enums.item import ItemStatus
from schemas.action import ActionCreateRequest
from schemas.item import ItemUpdateRequest


def test_valid_schemas_return_typed_internal_values():
    identity = uuid4()
    data = ActionCreateRequest.model_validate(
        {"itemId": str(identity), "name": "x" * 200, "type": "update"}
    )
    assert data.model_dump() == {
        "item_id": identity,
        "name": "x" * 200,
        "action_type": ActionType.UPDATE,
    }
    assert (
        ItemUpdateRequest.model_validate({"name": "example", "status": "archived"}).status
        is ItemStatus.ARCHIVED
    )
    assert [x.value for x in ItemStatus] == ["active", "archived"]
    assert [x.value for x in ActionType] == ["create", "update", "delete"]


@pytest.mark.parametrize(
    "body",
    [
        {"item_id": str(UUID(int=1)), "name": "x", "type": "create"},
        {"itemId": str(UUID(int=1)), "name": "x", "action_type": "create"},
    ],
)
def test_http_contracts_never_accept_internal_aliases(body):
    with pytest.raises(ValidationError):
        ActionCreateRequest.model_validate(body)


def test_action_list_preserves_aliases_and_freezes_resource():
    from schemas.action import ActionListResponse, ActionResponse

    payload = {
        "id": str(UUID(int=1)),
        "itemId": str(UUID(int=2)),
        "name": " x ",
        "type": "create",
        "createdAt": "2026-01-01T00:00:00+00:00",
        "updatedAt": "2026-01-01T00:00:00+00:00",
    }
    value = ActionResponse.model_validate(payload)
    assert ActionListResponse([value]).model_dump(mode="json", by_alias=True) == [payload]
    with pytest.raises(ValidationError):
        value.name = "changed"
