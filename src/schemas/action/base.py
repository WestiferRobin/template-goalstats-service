from pydantic import BaseModel, ConfigDict

from schemas.common import Identity


class ActionPathSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: Identity
