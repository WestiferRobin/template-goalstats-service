from marshmallow import Schema, fields


class ProblemSchema(Schema):
    type = fields.String(required=True)
    title = fields.String(required=True)
    status = fields.Integer(required=True)
    detail = fields.String(required=True)
