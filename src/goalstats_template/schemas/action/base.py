from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from goalstats_template.enums.action import ActionType

if TYPE_CHECKING:
    from goalstats_template.models import Action


@dataclass(frozen=True)
class ActionResult:
    id: UUID
    item_id: UUID
    name: str
    action_type: ActionType
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, action: "Action") -> "ActionResult":
        return cls(
            action.id,
            action.item_id,
            action.name,
            action.action_type,
            action.created_at,
            action.updated_at,
        )
