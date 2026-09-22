from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from enums.action import ActionType
from schemas.action.request import ActionCreateRequest, ActionWriteRequest


@pytest.mark.parametrize(
    "schema,body",
    [
        (ActionCreateRequest, {"name": "x", "type": "create"}),
        (ActionCreateRequest, {"name": "x", "type": "create", "itemId": "bad"}),
        (ActionCreateRequest, {"name": "x", "type": "create", "itemId": str(UUID(int=0))}),
        (ActionWriteRequest, {"name": "x", "type": "create", "itemId": str(uuid4())}),
        (ActionWriteRequest, {"name": "x", "type": "delete", "itemId": str(uuid4())}),
        (ActionWriteRequest, {"name": "x", "type": "0"}),
        (ActionWriteRequest, {"name": "x", "type": False}),
    ],
)
def test_action_request_rejects_invalid_values(schema, body):
    with pytest.raises(ValidationError):
        schema.model_validate(body)


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
