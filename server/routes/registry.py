#Dashboard routes for the trust features: batch code registry, agrovets, fake input reports, AI questions and USSD stats.
from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import Agrovet, AiQuestion, InputReport, UssdProfile, VerifiedProduct
from routes.auth import admin_required, current_user, login_required

bp = Blueprint("registry", __name__)


# Batch code registry
@bp.get("/batch-codes")
@login_required
def list_batch_codes():
    #Official batch code registry
    
    return paginate(VerifiedProduct.query.order_by(VerifiedProduct.created_at.desc())), 200


@bp.post("/batch-codes")
@admin_required
def add_batch_code():
    #Add a batch code from KEPHIS / PCPB / manufacturer records (admin only)
    
    data = get_data()
    product = VerifiedProduct(
        batch_code=data.get("batch_code"),
        product=data.get("product"),
        manufacturer=data.get("manufacturer"),
        status=data.get("status", "genuine"),
        added_by=current_user(),
    )
    db.session.add(product)
    db.session.commit()
    return product.to_dict(), 201


@bp.patch("/batch-codes/<int:product_id>")
@admin_required
def update_batch_code(product_id):
    #Edit a batch code, e.g. mark it fake (admin only)
    
    product = db.get_or_404(VerifiedProduct, product_id)
    data = get_data()
    for field in ("batch_code", "product", "manufacturer", "status"):
        if field in data:
            setattr(product, field, data[field])
    db.session.commit()
    return product.to_dict(), 200


@bp.delete("/batch-codes/<int:product_id>")
@admin_required
def delete_batch_code(product_id):
    #Delete a batch code (admin only)

    db.session.delete(db.get_or_404(VerifiedProduct, product_id))
    db.session.commit()
    return {}, 204


# Verified agrovets
@bp.get("/agrovets")
@login_required
def list_agrovets():
    #Verified agrovets
    
    return paginate(Agrovet.query.order_by(Agrovet.created_at.desc())), 200


@bp.post("/agrovets")
@admin_required
def add_agrovet():
    #Add a verified agrovet (admin only)

    data = get_data()
    agrovet = Agrovet(
        name=data.get("name"),
        ward=data.get("ward"),
        phone=data.get("phone"),
        license_no=data.get("license_no"),
        added_by=current_user(),
    )
    db.session.add(agrovet)
    db.session.commit()
    return agrovet.to_dict(), 201


@bp.patch("/agrovets/<int:agrovet_id>")
@admin_required
def update_agrovet(agrovet_id):
    #Edit an agrovet (admin only)
    
    agrovet = db.get_or_404(Agrovet, agrovet_id)
    data = get_data()
    for field in ("name", "ward", "phone", "license_no"):
        if field in data:
            setattr(agrovet, field, data[field])
    db.session.commit()
    return agrovet.to_dict(), 200


@bp.delete("/agrovets/<int:agrovet_id>")
@admin_required
def delete_agrovet(agrovet_id):
    #Remove an agrovet (admin only)
    
    db.session.delete(db.get_or_404(Agrovet, agrovet_id))
    db.session.commit()
    return {}, 204


# Reports from farmers
@bp.get("/input-reports")
@login_required
def list_input_reports():
    #Fake input / scam reports from USSD (phone numbers masked)
    
    query = InputReport.query
    kind = request.args.get("kind", "").strip()
    if kind:
        query = query.filter_by(kind=kind)
    return paginate(query.order_by(InputReport.created_at.desc())), 200


@bp.get("/ai-questions")
@login_required
def list_ai_questions():
    #Questions farmers asked the AI expert, with the answers sent
   
    return paginate(AiQuestion.query.order_by(AiQuestion.created_at.desc())), 200


@bp.get("/ussd-stats")
@login_required
def ussd_stats():
    #USSD numbers for the dashboard
    
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