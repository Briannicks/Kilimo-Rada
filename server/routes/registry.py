"""Dashboard routes for the trust features: batch code registry, agrovets,
fake input reports, AI questions and USSD stats."""
from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import Agrovet, AiQuestion, InputReport, UssdProfile, VerifiedProduct
from routes.auth import admin_required, current_user, login_required
from schemas.ussd_schemas import (
    agrovet_schema, ai_question_schema, batch_code_schema, input_report_schema,
)

bp = Blueprint("registry", __name__)


# ---------- batch code registry ----------
@bp.get("/batch-codes")
@login_required
def list_batch_codes():
    """Official batch code registry
    ---
    tags: [Trust]
    responses:
      200: {description: Paginated batch codes}
    """
    return paginate(VerifiedProduct.query.order_by(VerifiedProduct.created_at.desc()), batch_code_schema), 200


@bp.post("/batch-codes")
@admin_required
def add_batch_code():
    """Add a batch code from KEPHIS / PCPB / manufacturer records (admin only)
    ---
    tags: [Trust]
    parameters:
      - in: body
        name: body
        schema:
          example: {batch_code: ABC123, product: DAP 50kg, manufacturer: Company name, status: genuine}
    responses:
      201: {description: Added}
      409: {description: Code already exists}
    """
    data = batch_code_schema.load(get_data())
    product = VerifiedProduct(**data, added_by=current_user())
    db.session.add(product)
    db.session.commit()
    return batch_code_schema.dump(product), 201


@bp.patch("/batch-codes/<int:product_id>")
@admin_required
def update_batch_code(product_id):
    """Edit a batch code, e.g. mark it fake (admin only)
    ---
    tags: [Trust]
    parameters:
      - {name: product_id, in: path, type: integer, required: true}
      - in: body
        name: body
        schema:
          example: {status: fake}
    responses:
      200: {description: Updated}
    """
    product = db.get_or_404(VerifiedProduct, product_id)
    for field, value in batch_code_schema.load(get_data(), partial=True).items():
        setattr(product, field, value)
    db.session.commit()
    return batch_code_schema.dump(product), 200


@bp.delete("/batch-codes/<int:product_id>")
@admin_required
def delete_batch_code(product_id):
    """Delete a batch code (admin only)
    ---
    tags: [Trust]
    parameters:
      - {name: product_id, in: path, type: integer, required: true}
    responses:
      204: {description: Deleted}
    """
    db.session.delete(db.get_or_404(VerifiedProduct, product_id))
    db.session.commit()
    return {}, 204


# ---------- verified agrovets ----------
@bp.get("/agrovets")
@login_required
def list_agrovets():
    """Verified agrovets
    ---
    tags: [Trust]
    responses:
      200: {description: Paginated agrovets}
    """
    return paginate(Agrovet.query.order_by(Agrovet.created_at.desc()), agrovet_schema), 200


@bp.post("/agrovets")
@admin_required
def add_agrovet():
    """Add a verified agrovet (admin only)
    ---
    tags: [Trust]
    parameters:
      - in: body
        name: body
        schema:
          example: {name: Shop name, ward: Tinet, phone: "0712345678", license_no: PCPB-123}
    responses:
      201: {description: Added}
    """
    data = agrovet_schema.load(get_data())
    agrovet = Agrovet(**data, added_by=current_user())
    db.session.add(agrovet)
    db.session.commit()
    return agrovet_schema.dump(agrovet), 201


@bp.patch("/agrovets/<int:agrovet_id>")
@admin_required
def update_agrovet(agrovet_id):
    """Edit an agrovet (admin only)
    ---
    tags: [Trust]
    parameters:
      - {name: agrovet_id, in: path, type: integer, required: true}
    responses:
      200: {description: Updated}
    """
    agrovet = db.get_or_404(Agrovet, agrovet_id)
    for field, value in agrovet_schema.load(get_data(), partial=True).items():
        setattr(agrovet, field, value)
    db.session.commit()
    return agrovet_schema.dump(agrovet), 200


@bp.delete("/agrovets/<int:agrovet_id>")
@admin_required
def delete_agrovet(agrovet_id):
    """Remove an agrovet (admin only)
    ---
    tags: [Trust]
    parameters:
      - {name: agrovet_id, in: path, type: integer, required: true}
    responses:
      204: {description: Deleted}
    """
    db.session.delete(db.get_or_404(Agrovet, agrovet_id))
    db.session.commit()
    return {}, 204


# ---------- reports from farmers ----------
@bp.get("/input-reports")
@login_required
def list_input_reports():
    """Fake input / scam reports from USSD (phone numbers masked)
    ---
    tags: [Trust]
    parameters:
      - {name: kind, in: query, type: string, enum: [batch_code, scam_number]}
    responses:
      200: {description: Paginated reports}
    """
    query = InputReport.query
    kind = request.args.get("kind", "").strip()
    if kind:
        query = query.filter_by(kind=kind)
    return paginate(query.order_by(InputReport.created_at.desc()), input_report_schema), 200


@bp.get("/ai-questions")
@login_required
def list_ai_questions():
    """Questions farmers asked the AI expert, with the answers sent
    ---
    tags: [Trust]
    responses:
      200: {description: Paginated questions}
    """
    return paginate(AiQuestion.query.order_by(AiQuestion.created_at.desc()), ai_question_schema), 200


@bp.get("/ussd-stats")
@login_required
def ussd_stats():
    """USSD numbers for the dashboard
    ---
    tags: [Trust]
    responses:
      200: {description: Counts and most-reported codes}
    """
    count = db.func.count(InputReport.id)
    most_reported = (
        db.session.query(InputReport.value, InputReport.kind, count)
        .group_by(InputReport.value, InputReport.kind)
        .order_by(count.desc())
        .limit(5)
        .all()
    )
    return {
        "ussd_users": UssdProfile.query.count(),
        "ai_questions": AiQuestion.query.count(),
        "fake_input_reports": InputReport.query.count(),
        "batch_codes_registered": VerifiedProduct.query.count(),
        "verified_agrovets": Agrovet.query.count(),
        "most_reported": [
            {"value": value, "kind": kind, "reports": total, "flagged": total >= 3}
            for value, kind, total in most_reported
        ],
    }, 200