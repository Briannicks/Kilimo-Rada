from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import Farmer, Report
from routes.auth import admin_required, current_user, login_required
from services import send_sms

bp = Blueprint("reports", __name__)


@bp.get("/reports")
@login_required
def list_reports():
    """Reports inbox with filters and pagination
    ---
    tags: [Reports]
    parameters:
      - {name: status, in: query, type: string, enum: [open, resolved]}
      - {name: category, in: query, type: string, enum: [pest, disease, weather, other]}
      - {name: ward, in: query, type: string}
      - {name: page, in: query, type: integer}
      - {name: per_page, in: query, type: integer}
    responses:
      200: {description: Paginated reports}
    """
    query = Report.query

    status = request.args.get("status", "").strip()
    if status:
        query = query.filter_by(status=status)
    category = request.args.get("category", "").strip()
    if category:
        query = query.filter_by(category=category)
    ward = request.args.get("ward", "").strip()
    if ward:
        query = query.join(Farmer).filter(Farmer.ward.ilike(ward))

    return paginate(query.order_by(Report.created_at.desc())), 200


@bp.post("/reports")
@login_required
def create_report():
    """Log a report from the dashboard (e.g. a farmer phoned in)
    ---
    tags: [Reports]
    parameters:
      - in: body
        name: body
        schema:
          example: {farmer_id: 1, category: pest, description: Aphids on beans}
    responses:
      201: {description: Report created}
      404: {description: Farmer not found}
    """
    data = get_data()
    farmer = db.get_or_404(Farmer, data.get("farmer_id"))
    report = Report(
        farmer=farmer,
        category=data.get("category"),
        description=data.get("description"),
    )
    db.session.add(report)
    db.session.commit()
    return report.to_dict(), 201


@bp.get("/reports/<int:report_id>")
@login_required
def get_report(report_id):
    """One report
    ---
    tags: [Reports]
    parameters:
      - {name: report_id, in: path, type: integer, required: true}
    responses:
      200: {description: Report details}
      404: {description: Not found}
    """
    return db.get_or_404(Report, report_id).to_dict(), 200


@bp.patch("/reports/<int:report_id>")
@login_required
def update_report(report_id):
    """Change a report's status or category
    ---
    tags: [Reports]
    parameters:
      - {name: report_id, in: path, type: integer, required: true}
      - in: body
        name: body
        schema:
          example: {status: resolved}
    responses:
      200: {description: Updated}
      422: {description: Invalid status or category}
    """
    report = db.get_or_404(Report, report_id)
    data = get_data()
    if "status" in data:
        report.status = data["status"]
    if "category" in data:
        report.category = data["category"]
    db.session.commit()
    return report.to_dict(), 200


@bp.post("/reports/<int:report_id>/reply")
@login_required
def reply_to_report(report_id):
    """Reply to a farmer: saves the reply, sends it by SMS and marks the report resolved
    ---
    tags: [Reports]
    parameters:
      - {name: report_id, in: path, type: integer, required: true}
      - in: body
        name: body
        schema:
          example: {message: Spray with an approved pesticide and remove affected leaves.}
    responses:
      200: {description: Reply saved and SMS sent}
      422: {description: Empty or too long}
    """
    report = db.get_or_404(Report, report_id)
    message = (get_data().get("message") or "").strip()
    if not message:
        return {"error": "Reply message cannot be empty"}, 422
    if len(message) > 450:
        return {"error": "Reply must be 450 characters or less"}, 422

    report.reply = message
    report.replied_by = current_user()
    report.status = "resolved"
    db.session.commit()

    sms_result = send_sms([report.farmer.phone], f"KilimoRada: {message}")
    result = report.to_dict()
    result["sms"] = sms_result
    return result, 200


@bp.delete("/reports/<int:report_id>")
@admin_required
def delete_report(report_id):
    """Delete a report (admin only)
    ---
    tags: [Reports]
    parameters:
      - {name: report_id, in: path, type: integer, required: true}
    responses:
      204: {description: Deleted}
      403: {description: Admins only}
    """
    report = db.get_or_404(Report, report_id)
    db.session.delete(report)
    db.session.commit()
    return {}, 204
