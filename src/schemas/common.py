"""Shared input constraints and compatible timestamp serialization."""

from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, Field, PlainSerializer, WithJsonSchema


def nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Name must be nonblank.")
    return value


def nonzero(value: UUID) -> UUID:
    if value.int == 0:
        raise ValueError("A nonempty UUID is required.")
    return value


Name = Annotated[str, Field(strict=True, min_length=1, max_length=200), AfterValidator(nonblank)]
Identity = Annotated[UUID, AfterValidator(nonzero)]
Timestamp = Annotated[
    AwareDatetime,
    PlainSerializer(lambda value: value.isoformat(), return_type=str),
    WithJsonSchema({"type": "string", "format": "date-time"}, mode="serialization"),
]
