from marshmallow import fields, validate

from goalstats_template.enums import ActionType
from goalstats_template.schemas.common import RequestSchema, identity, name


class NestedActionSchema(RequestSchema):
    name = fields.String(required=True, validate=[validate.Length(min=1, max=200), name])
    action_type = fields.Enum(ActionType, by_value=True, required=True, data_key="type")


class CreateActionSchema(NestedActionSchema):
    item_id = fields.UUID(required=True, validate=identity, data_key="itemId")


class UpdateActionSchema(NestedActionSchema):
    pass


class ActionResponseSchema(CreateActionSchema):
    id = fields.UUID(required=True, validate=identity)
    created_at = fields.AwareDateTime(required=True, data_key="createdAt")
    updated_at = fields.AwareDateTime(required=True, data_key="updatedAt")
