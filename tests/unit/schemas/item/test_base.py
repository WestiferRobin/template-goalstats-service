from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas.item.base import ItemPathSchema


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"item_id": "bad"},
        {"item_id": str(UUID(int=0))},
        {"item_id": str(UUID(int=1)), "extra": 1},
    ],
)
def test_path_rejects_invalid_identifiers_and_extras(body):
    with pytest.raises(ValidationError):
        ItemPathSchema.model_validate(body)


@pytest.mark.parametrize("identity", [UUID(int=1), str(UUID(int=1))])
def test_path_preserves_typed_identity(identity):
    assert ItemPathSchema(item_id=identity).item_id == UUID(int=1)
