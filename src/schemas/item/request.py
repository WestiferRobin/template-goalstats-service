from marshmallow import fields, validate

from enums.item import ItemStatus
from schemas.base import RequestSchema, name


class CreateItemSchema(RequestSchema):
    name = fields.String(required=True, validate=[validate.Length(min=1, max=200), name])


class UpdateItemSchema(CreateItemSchema):
    status = fields.Enum(ItemStatus, by_value=True, required=True)
