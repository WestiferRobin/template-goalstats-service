from pydantic import BaseModel, ConfigDict, Field, RootModel

from enums.item import ItemStatus
from schemas.common import Identity, Name, Timestamp


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name


class ItemUpdate(ItemCreate):
    status: ItemStatus


class ItemResponse(ItemUpdate):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    id: Identity
    created_at: Timestamp = Field(validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: Timestamp = Field(validation_alias="updatedAt", serialization_alias="updatedAt")


class ItemPath(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: Identity


class ItemListResponse(RootModel[list[ItemResponse]]):
    pass
