from marshmallow import fields, validate

from schemas.base import BaseSchema


class FarmerSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    phone = fields.Str(required=True, validate=validate.Length(min=9, max=20))
    ward = fields.Str(allow_none=True, validate=validate.Length(max=100))
    main_crop = fields.Str(allow_none=True, validate=validate.Length(max=50))
    registered_via = fields.Str(dump_only=True)
    added_by_id = fields.Int(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


farmer_schema = FarmerSchema()