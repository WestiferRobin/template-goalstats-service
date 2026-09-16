from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from enums.item import ItemStatus

if TYPE_CHECKING:
    from models import Item


@dataclass(frozen=True)
class ItemResult:
    id: UUID
    name: str
    status: ItemStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, item: "Item") -> "ItemResult":
        return cls(item.id, item.name, item.status, item.created_at, item.updated_at)
