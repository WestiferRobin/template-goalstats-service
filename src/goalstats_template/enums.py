from enum import StrEnum


class ItemStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ActionType(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
