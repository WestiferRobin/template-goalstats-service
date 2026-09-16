from marshmallow import fields

from schemas.base import identity
from schemas.item.request import UpdateItemSchema


class ItemResponseSchema(UpdateItemSchema):
    id = fields.UUID(required=True, validate=identity)
    created_at = fields.AwareDateTime(required=True, data_key="createdAt")
    updated_at = fields.AwareDateTime(required=True, data_key="updatedAt")
