"""Framework-independent application errors with safe public messages."""


class DomainError(Exception):
    """Subclass with a reviewed public message; constructor details remain private."""

    public_detail = "The operation could not be completed."


class RequestValidationError(DomainError):
    public_detail = "The request contains invalid values."


class ItemNotFound(DomainError):
    public_detail = "Item was not found."


class ActionNotFound(DomainError):
    public_detail = "Action was not found."
