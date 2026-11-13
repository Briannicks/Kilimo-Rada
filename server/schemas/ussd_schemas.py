from marshmallow import fields, validate

from models import mask_phone
from schemas.base import BaseSchema


class BroadcastSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    message = fields.Str(required=True, validate=validate.Length(min=1, max=160))
    target_crop = fields.Str(allow_none=True, load_default=None)  # null = all farmers
    recipient_count = fields.Int(dump_only=True)
    sender = fields.Function(
        lambda broadcast: broadcast.sender.name if broadcast.sender else None, dump_only=True
    )
    created_at = fields.DateTime(dump_only=True)


class BatchCodeSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    batch_code = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    product = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    manufacturer = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    status = fields.Str(load_default="genuine", validate=validate.OneOf(["genuine", "fake"]))
    added_by = fields.Function(
        lambda product: product.added_by.name if product.added_by else None, dump_only=True
    )
    created_at = fields.DateTime(dump_only=True)


class AgrovetSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    ward = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    phone = fields.Str(required=True)
    license_no = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class InputReportSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    reference = fields.Str(dump_only=True)
    reported_by = fields.Function(lambda report: mask_phone(report.phone), dump_only=True)
    kind = fields.Str(dump_only=True)
    value = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class AiQuestionSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    phone = fields.Function(lambda question: mask_phone(question.phone), dump_only=True)
    question = fields.Str(dump_only=True)
    answer = fields.Str(dump_only=True, allow_none=True)
    language = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


broadcast_schema = BroadcastSchema()
batch_code_schema = BatchCodeSchema()
agrovet_schema = AgrovetSchema()
input_report_schema = InputReportSchema()
ai_question_schema = AiQuestionSchema()