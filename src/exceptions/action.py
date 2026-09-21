from exceptions.base import DomainError


class ActionNotFound(DomainError):
    public_detail = "Action was not found."
