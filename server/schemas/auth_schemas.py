from marshmallow import fields, validate

from kenya import COUNTIES
from schemas.base import BaseSchema


class SignupSchema(BaseSchema):
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8, max=128))
    county = fields.String(
        required=True,
        validate=validate.OneOf(COUNTIES, error="Choose a county from the list"),
    )
    ward = fields.String(required=True, validate=validate.Length(min=2, max=100))


class LoginSchema(BaseSchema):
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)


class VerifyCodeSchema(BaseSchema):
    code = fields.String(
        required=True,
        validate=validate.Regexp(r"^\d{6}$", error="Enter the 6-digit code"),
    )


class UserSchema(BaseSchema):
    """What the API sends back for a user (never the password or code)."""
    id = fields.Integer(dump_only=True)
    name = fields.String()
    email = fields.String()
    role = fields.String()
    avatar_url = fields.String(allow_none=True)
    county = fields.String(allow_none=True)
    ward = fields.String(allow_none=True)
    is_email_verified = fields.Boolean()
    is_approved = fields.Boolean()
    created_at = fields.DateTime()


class ProfileUpdateSchema(BaseSchema):
    name = fields.String(validate=validate.Length(min=2, max=100))
    county = fields.String(validate=validate.OneOf(COUNTIES, error="Choose a county from the list"))
    ward = fields.String(validate=validate.Length(min=2, max=100))


class RoleSchema(BaseSchema):
    role = fields.String(required=True, validate=validate.OneOf(("admin", "officer")))


user_schema = UserSchema()
users_schema = UserSchema(many=True)