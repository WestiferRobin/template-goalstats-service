from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from schemas.common import Identity, Name, Timestamp


@pytest.mark.parametrize("value", [None, "", " \t\n", "x" * 201, 12])
def test_name_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        TypeAdapter(Name).validate_python(value)


def test_name_preserves_whitespace_and_accepts_maximum_length():
    adapter = TypeAdapter(Name)
    assert adapter.validate_python(" x ") == " x "
    assert adapter.validate_python("x" * 200) == "x" * 200


@pytest.mark.parametrize("value", [None, "bad", str(UUID(int=0))])
def test_identity_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        TypeAdapter(Identity).validate_python(value)


def test_identity_accepts_uuid_objects_and_strings():
    adapter = TypeAdapter(Identity)
    identity = UUID(int=1)
    assert adapter.validate_python(identity) == identity
    assert adapter.validate_python(str(identity)) == identity


def test_timestamp_requires_timezone_and_preserves_offset_serialization():
    adapter = TypeAdapter(Timestamp)
    value = datetime(2026, 1, 1, tzinfo=UTC)
    assert adapter.validate_python(value.isoformat()) == value
    assert adapter.dump_python(value, mode="json") == "2026-01-01T00:00:00+00:00"
    with pytest.raises(ValidationError):
        adapter.validate_python("2026-01-01T00:00:00")
