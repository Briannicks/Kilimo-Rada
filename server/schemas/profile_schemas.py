from marshmallow import fields, validate

from schemas.base import BaseSchema


class RoleSchema(BaseSchema):
    role = fields.Str(required=True, validate=validate.OneOf(["admin", "officer"]))


class ProfileSchema(BaseSchema):
    name = fields.Str(validate=validate.Length(min=2, max=100))


role_schema = RoleSchema()
profile_schema = ProfileSchema()