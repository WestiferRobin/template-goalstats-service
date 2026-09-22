from pydantic import ConfigDict, Field, RootModel

from schemas.action.request import ActionCreateRequest
from schemas.common import Identity, Timestamp


class ActionResponse(ActionCreateRequest):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    id: Identity
    created_at: Timestamp = Field(alias="createdAt")
    updated_at: Timestamp = Field(alias="updatedAt")


class ActionListResponse(RootModel[list[ActionResponse]]):
    pass
