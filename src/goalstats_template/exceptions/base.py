"""Framework-independent application errors with safe public messages."""


class DomainError(Exception):
    """Subclass with a reviewed public message; constructor details remain private."""

    status = 400
    public_detail = "The operation could not be completed."


class RequestValidationError(DomainError):
    public_detail = "The request contains invalid values."


class ItemNotFound(DomainError):
    status = 404
    public_detail = "Item was not found."


class ActionNotFound(DomainError):
    status = 404
    public_detail = "Action was not found."
