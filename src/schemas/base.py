from uuid import UUID

from marshmallow import RAISE, Schema, ValidationError

from exceptions.base import RequestValidationError
from services.item.validation import require_id, require_name


class RequestSchema(Schema):
    class Meta:
        unknown = RAISE


def name(value: str) -> None:
    try:
        require_name(value)
    except RequestValidationError:
        raise ValidationError("Name must be nonblank and at most 200 characters.") from None


def identity(value: UUID) -> None:
    try:
        require_id(value)
    except RequestValidationError:
        raise ValidationError("A nonempty UUID is required.") from None
