from pydantic import BaseModel, ConfigDict, Field

from enums.action import ActionType
from schemas.common import Identity, Name


class ActionWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=False)
    name: Name
    action_type: ActionType = Field(alias="type")


class ActionCreateRequest(ActionWriteRequest):
    item_id: Identity = Field(alias="itemId")
