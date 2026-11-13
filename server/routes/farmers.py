from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import Farmer
from routes.auth import admin_required, current_user, login_required
from schemas.farmer_schemas import farmer_schema
from schemas.report_schemas import report_schema

bp = Blueprint("farmers", __name__)


@bp.get("/farmers")
@login_required
def list_farmers():
    """List farmers with search, filters and pagination
    ---
    tags: [Farmers]
    parameters:
      - {name: search, in: query, type: string, description: name or phone}
      - {name: ward, in: query, type: string}
      - {name: crop, in: query, type: string}
      - {name: page, in: query, type: integer}
      - {name: per_page, in: query, type: integer}
    responses:
      200: {description: Paginated farmers}
    """
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

    return paginate(query.order_by(Farmer.created_at.desc()), farmer_schema), 200


@bp.post("/farmers")
@login_required
def create_farmer():
    """Register a farmer from the dashboard
    ---
    tags: [Farmers]
    parameters:
      - in: body
        name: body
        schema:
          example: {name: John Kiprop, phone: "0712345678", ward: Tinet, main_crop: Maize}
    responses:
      201: {description: Farmer created}
      409: {description: Phone already registered}
      422: {description: Invalid data}
    """
    data = farmer_schema.load(get_data())
    if Farmer.query.filter_by(phone=Farmer.normalize_phone(data["phone"])).first():
        return {"error": "A farmer with this phone number already exists"}, 409

    farmer = Farmer(**data, registered_via="web", added_by=current_user())
    db.session.add(farmer)
    db.session.commit()
    return farmer_schema.dump(farmer), 201


@bp.get("/farmers/<int:farmer_id>")
@login_required
def get_farmer(farmer_id):
    """One farmer with their reports
    ---
    tags: [Farmers]
    parameters:
      - {name: farmer_id, in: path, type: integer, required: true}
    responses:
      200: {description: Farmer details}
      404: {description: Not found}
    """
    farmer = db.get_or_404(Farmer, farmer_id)
    result = farmer_schema.dump(farmer)
    result["reports"] = report_schema.dump(farmer.reports, many=True)
    return result, 200


@bp.patch("/farmers/<int:farmer_id>")
@login_required
def update_farmer(farmer_id):
    """Edit a farmer
    ---
    tags: [Farmers]
    parameters:
      - {name: farmer_id, in: path, type: integer, required: true}
      - in: body
        name: body
        schema:
          example: {ward: Lanet, main_crop: Beans}
    responses:
      200: {description: Updated}
      409: {description: Phone already used}
      422: {description: Invalid data}
    """
    farmer = db.get_or_404(Farmer, farmer_id)
    data = farmer_schema.load(get_data(), partial=True)

    if "phone" in data:
        existing = Farmer.query.filter_by(phone=Farmer.normalize_phone(data["phone"])).first()
        if existing and existing.id != farmer.id:
            return {"error": "Another farmer already uses this phone number"}, 409

    for field, value in data.items():
        setattr(farmer, field, value)

    db.session.commit()
    return farmer_schema.dump(farmer), 200


@bp.delete("/farmers/<int:farmer_id>")
@admin_required
def delete_farmer(farmer_id):
    """Delete a farmer and their reports (admin only)
    ---
    tags: [Farmers]
    parameters:
      - {name: farmer_id, in: path, type: integer, required: true}
    responses:
      204: {description: Deleted}
      403: {description: Admins only}
    """
    farmer = db.get_or_404(Farmer, farmer_id)
    db.session.delete(farmer)
    db.session.commit()
    return {}, 204