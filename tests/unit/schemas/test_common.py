from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from schemas.action import ActionCreateRequest, ActionWriteRequest
from schemas.item import ItemCreateRequest, ItemUpdateRequest


@pytest.mark.parametrize(
    "schema,body",
    [
        (ItemCreateRequest, {}),
        (ItemCreateRequest, {"name": None}),
        (ItemCreateRequest, {"name": ""}),
        (ItemCreateRequest, {"name": " \t\n"}),
        (ItemCreateRequest, {"name": "x" * 201}),
        (ItemCreateRequest, {"name": 12}),
        (ItemCreateRequest, {"name": "x", "extra": 1}),
        (ItemUpdateRequest, {"name": "x"}),
        (ItemUpdateRequest, {"name": "x", "status": "0"}),
        (ItemUpdateRequest, {"name": "x", "status": 0}),
        (ItemUpdateRequest, {"name": "x", "status": "invalid"}),
        (ActionCreateRequest, {"name": "x", "type": "create"}),
        (ActionCreateRequest, {"name": "x", "type": "create", "itemId": "bad"}),
        (ActionCreateRequest, {"name": "x", "type": "create", "itemId": str(UUID(int=0))}),
        (ActionWriteRequest, {"name": "x", "type": "create", "itemId": str(uuid4())}),
        (ActionWriteRequest, {"name": "x", "type": "delete", "itemId": str(uuid4())}),
        (ActionWriteRequest, {"name": "x", "type": "0"}),
        (ActionWriteRequest, {"name": "x", "type": False}),
    ],
)
def test_request_contract_rejects_invalid_values(schema, body):
    with pytest.raises(ValidationError):
        schema.model_validate(body)
