from pydantic import BaseModel, ConfigDict, Field, RootModel

from enums.action import ActionType
from schemas.common import Identity, Name, Timestamp


class ActionWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=False)
    name: Name
    action_type: ActionType = Field(alias="type")


class ActionCreateRequest(ActionWriteRequest):
    item_id: Identity = Field(alias="itemId")


class ActionResponse(ActionCreateRequest):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    id: Identity
    created_at: Timestamp = Field(alias="createdAt")
    updated_at: Timestamp = Field(alias="updatedAt")


class ActionPathSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: Identity


class ActionListResponse(RootModel[list[ActionResponse]]):
    pass
