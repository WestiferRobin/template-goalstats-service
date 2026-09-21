from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas.action.base import ActionPathSchema


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"action_id": "bad"},
        {"action_id": str(UUID(int=0))},
        {"action_id": str(UUID(int=1)), "extra": 1},
    ],
)
def test_path_rejects_invalid_identifiers_and_extras(body):
    with pytest.raises(ValidationError):
        ActionPathSchema.model_validate(body)


@pytest.mark.parametrize("identity", [UUID(int=1), str(UUID(int=1))])
def test_path_preserves_typed_identity(identity):
    assert ActionPathSchema(action_id=identity).action_id == UUID(int=1)
