from exceptions.base import DomainError


class ItemNotFound(DomainError):
    public_detail = "Item was not found."
