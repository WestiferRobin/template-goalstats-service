from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError


def test_action_list_preserves_aliases_and_freezes_resource():
    from schemas.action.response import ActionListResponse, ActionResponse

    payload = {
        "id": str(UUID(int=1)),
        "itemId": str(UUID(int=2)),
        "name": " x ",
        "type": "create",
        "createdAt": "2026-01-01T00:00:00+00:00",
        "updatedAt": "2026-01-01T00:00:00+00:00",
    }
    value = ActionResponse.model_validate(payload)
    assert value.model_dump(mode="json", by_alias=True) == payload
    row = SimpleNamespace(
        id=UUID(int=1),
        item_id=UUID(int=2),
        name=" x ",
        action_type="create",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert ActionResponse.model_validate(row, by_name=True, by_alias=False) == value
    with pytest.raises(ValidationError):
        ActionResponse.model_validate({**payload, "createdAt": "2026-01-01T00:00:00"})
    assert ActionListResponse([value]).model_dump(mode="json", by_alias=True) == [payload]
    with pytest.raises(ValidationError):
        value.name = "changed"
