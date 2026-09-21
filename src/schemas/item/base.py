from pydantic import BaseModel, ConfigDict

from schemas.common import Identity


class ItemPathSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: Identity
