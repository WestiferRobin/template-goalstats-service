from pydantic import BaseModel, ConfigDict, Field, RootModel

from enums.item import ItemStatus
from schemas.common import Identity, Name, Timestamp


class ItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name


class ItemUpdateRequest(ItemCreateRequest):
    status: ItemStatus


class ItemResponse(ItemUpdateRequest):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    id: Identity
    created_at: Timestamp = Field(validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: Timestamp = Field(validation_alias="updatedAt", serialization_alias="updatedAt")


class ItemPathSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: Identity


class ItemListResponse(RootModel[list[ItemResponse]]):
    pass
