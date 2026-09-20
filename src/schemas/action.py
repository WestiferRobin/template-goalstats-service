from pydantic import BaseModel, ConfigDict, Field, RootModel

from enums.action import ActionType
from schemas.common import Identity, Name, Timestamp


class ActionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=False)
    name: Name
    action_type: ActionType = Field(alias="type")


class ActionCreate(ActionWrite):
    item_id: Identity = Field(alias="itemId")


class ActionResponse(ActionCreate):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    id: Identity
    created_at: Timestamp = Field(alias="createdAt")
    updated_at: Timestamp = Field(alias="updatedAt")


class ActionPath(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: Identity


class ActionListResponse(RootModel[list[ActionResponse]]):
    pass
