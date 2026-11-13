from marshmallow import fields, validate

from schemas.base import BaseSchema

CATEGORIES = ["pest", "disease", "weather", "other"]
STATUSES = ["open", "resolved"]


class FarmerSummarySchema(BaseSchema):
    """The short farmer info shown inside a report."""
    id = fields.Int()
    name = fields.Str()
    phone = fields.Str()
    ward = fields.Str(allow_none=True)


class ReportSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    farmer_id = fields.Int(required=True, load_only=True)
    category = fields.Str(load_default="other", validate=validate.OneOf(CATEGORIES))
    description = fields.Str(required=True, validate=validate.Length(min=3))
    status = fields.Str(validate=validate.OneOf(STATUSES))
    reply = fields.Str(dump_only=True, allow_none=True)
    replied_by = fields.Function(
        lambda report: report.replied_by.name if report.replied_by else None, dump_only=True
    )
    created_at = fields.DateTime(dump_only=True)
    farmer = fields.Nested(FarmerSummarySchema, dump_only=True)


class ReportUpdateSchema(BaseSchema):
    status = fields.Str(validate=validate.OneOf(STATUSES))
    category = fields.Str(validate=validate.OneOf(CATEGORIES))


class ReplySchema(BaseSchema):
    message = fields.Str(required=True, validate=validate.Length(min=1, max=450))


class MarketPriceSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    crop = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    market = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    unit = fields.Str(required=True, validate=validate.Length(min=1, max=30))
    price = fields.Int(required=True, validate=validate.Range(min=1))
    user_id = fields.Int(dump_only=True)
    posted_by = fields.Function(
        lambda price: price.owner.name if price.owner else None, dump_only=True
    )
    updated_at = fields.DateTime(dump_only=True)


report_schema = ReportSchema()
report_update_schema = ReportUpdateSchema()
reply_schema = ReplySchema()
price_schema = MarketPriceSchema()