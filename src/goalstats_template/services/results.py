from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from goalstats_template.enums import ActionType, ItemStatus
from goalstats_template.models import Action, Item


@dataclass(frozen=True)
class ItemResult:
    id: UUID
    name: str
    status: ItemStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, item: Item) -> "ItemResult":
        return cls(item.id, item.name, item.status, item.created_at, item.updated_at)


@dataclass(frozen=True)
class ActionResult:
    id: UUID
    item_id: UUID
    name: str
    action_type: ActionType
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, action: Action) -> "ActionResult":
        return cls(
            action.id,
            action.item_id,
            action.name,
            action.action_type,
            action.created_at,
            action.updated_at,
        )
