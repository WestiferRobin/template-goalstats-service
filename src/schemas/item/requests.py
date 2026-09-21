from pydantic import BaseModel, ConfigDict

from enums.item import ItemStatus
from schemas.common import Name


class ItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name


class ItemUpdateRequest(ItemCreateRequest):
    status: ItemStatus
