from uuid import UUID

from exceptions.base import RequestValidationError


def require_name(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise RequestValidationError()


def require_id(value: UUID) -> None:
    if not isinstance(value, UUID) or value.int == 0:
        raise RequestValidationError()
