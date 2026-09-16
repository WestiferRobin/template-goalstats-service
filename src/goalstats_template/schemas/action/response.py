from marshmallow import fields

from goalstats_template.schemas.action.request import CreateActionSchema
from goalstats_template.schemas.base import identity


class ActionResponseSchema(CreateActionSchema):
    id = fields.UUID(required=True, validate=identity)
    created_at = fields.AwareDateTime(required=True, data_key="createdAt")
    updated_at = fields.AwareDateTime(required=True, data_key="updatedAt")
