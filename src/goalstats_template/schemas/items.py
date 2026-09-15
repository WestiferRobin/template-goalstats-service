from marshmallow import fields, validate

from goalstats_template.enums import ItemStatus
from goalstats_template.schemas.common import RequestSchema, identity, name


class CreateItemSchema(RequestSchema):
    name = fields.String(required=True, validate=[validate.Length(min=1, max=200), name])


class UpdateItemSchema(CreateItemSchema):
    status = fields.Enum(ItemStatus, by_value=True, required=True)


class ItemResponseSchema(UpdateItemSchema):
    id = fields.UUID(required=True, validate=identity)
    created_at = fields.AwareDateTime(required=True, data_key="createdAt")
    updated_at = fields.AwareDateTime(required=True, data_key="updatedAt")
