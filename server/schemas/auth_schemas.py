from marshmallow import fields, validate

from schemas.base import BaseSchema


class UserSchema(BaseSchema):
    """What the API returns for a user. password_hash and otp_hash are never included."""
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    email = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)
    avatar_url = fields.Str(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class SignupSchema(BaseSchema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8))


class LoginSchema(BaseSchema):
    email = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)


class OtpSchema(BaseSchema):
    code = fields.Str(required=True, validate=validate.Length(equal=6))


user_schema = UserSchema()
signup_schema = SignupSchema()
login_schema = LoginSchema()
otp_schema = OtpSchema()