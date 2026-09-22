from pydantic import ConfigDict, Field, RootModel

from schemas.common import Identity, Timestamp
from schemas.item.request import ItemUpdateRequest


class ItemResponse(ItemUpdateRequest):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    id: Identity
    created_at: Timestamp = Field(validation_alias="createdAt", serialization_alias="createdAt")
    updated_at: Timestamp = Field(validation_alias="updatedAt", serialization_alias="updatedAt")


class ItemListResponse(RootModel[list[ItemResponse]]):
    pass
