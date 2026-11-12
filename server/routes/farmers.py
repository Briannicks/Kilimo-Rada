from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import Farmer
from routes.auth import admin_required, current_user, login_required

bp = Blueprint("farmers", __name__)

EDITABLE_FIELDS = ("name", "phone", "ward", "main_crop")

#List farmers with search, filters and pagination
@bp.get("/farmers")
@login_required
def list_farmers():
    
    query = Farmer.query

    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(db.or_(
            Farmer.name.ilike(f"%{search}%"),
            Farmer.phone.ilike(f"%{search}%"),
        ))
    ward = request.args.get("ward", "").strip()
    if ward:
        query = query.filter(Farmer.ward.ilike(ward))
    crop = request.args.get("crop", "").strip()
    if crop:
        query = query.filter(Farmer.main_crop.ilike(crop))

    return paginate(query.order_by(Farmer.created_at.desc())), 200

#Register a farmer from the dashboard
@bp.post("/farmers")
@login_required
def create_farmer():
    
    data = get_data()
    phone = Farmer.normalize_phone(data.get("phone"))
    if Farmer.query.filter_by(phone=phone).first():
        return {"error": "A farmer with this phone number already exists"}, 409

    farmer = Farmer(
        name=data.get("name"),
        phone=phone,
        ward=data.get("ward"),
        main_crop=data.get("main_crop"),
        registered_via="web",
        added_by=current_user(),
    )
    db.session.add(farmer)
    db.session.commit()
    return farmer.to_dict(), 201

#One farmer with their reports
@bp.get("/farmers/<int:farmer_id>")
@login_required
def get_farmer(farmer_id):
    
    farmer = db.get_or_404(Farmer, farmer_id)
    result = farmer.to_dict()
    result["reports"] = [report.to_dict() for report in farmer.reports]
    return result, 200

#Edit a farmer
@bp.patch("/farmers/<int:farmer_id>")
@login_required
def update_farmer(farmer_id):
    
    farmer = db.get_or_404(Farmer, farmer_id)
    data = get_data()

    if "phone" in data:
        phone = Farmer.normalize_phone(data["phone"])
        existing = Farmer.query.filter_by(phone=phone).first()
        if existing and existing.id != farmer.id:
            return {"error": "Another farmer already uses this phone number"}, 409

    for field in EDITABLE_FIELDS:
        if field in data:
            setattr(farmer, field, data[field])

    db.session.commit()
    return farmer.to_dict(), 200

#Delete a farmer and their reports (admin only)
@bp.delete("/farmers/<int:farmer_id>")
@admin_required
def delete_farmer(farmer_id):
    
    farmer = db.get_or_404(Farmer, farmer_id)
    db.session.delete(farmer)
    db.session.commit()
    return {}, 204