import pytest
from pydantic import ValidationError

from enums.item import ItemStatus
from schemas.item.request import ItemCreateRequest, ItemUpdateRequest


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
    ],
)
def test_item_request_rejects_invalid_values(schema, body):
    with pytest.raises(ValidationError):
        schema.model_validate(body)


def test_item_requests_return_typed_values():
    assert ItemCreateRequest(name=" x ").name == " x "
    assert ItemCreateRequest(name="x" * 200).name == "x" * 200
    assert (
        ItemUpdateRequest.model_validate({"name": "example", "status": "archived"}).status
        is ItemStatus.ARCHIVED
    )
    assert [x.value for x in ItemStatus] == ["active", "archived"]
