from uuid import UUID

import pytest
from pydantic import ValidationError

from enums.item import ItemStatus


def test_responses_are_detached_frozen_and_preserve_wire_timestamps():
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from schemas.item.response import ItemListResponse, ItemResponse

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
