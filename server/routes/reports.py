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
    #Reports inbox with filters and pagination
    
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
    #Log a report from the dashboard (e.g. a farmer phoned in)
    
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
    # Get one report
    
    return db.get_or_404(Report, report_id).to_dict(), 200


@bp.patch("/reports/<int:report_id>")
@login_required
def update_report(report_id):
    #Change a report's status or category
    
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
    #Reply to a farmer: saves the reply, sends it by SMS and marks the report resolved
    
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
    #Delete a report (admin only)
     
    report = db.get_or_404(Report, report_id)
    db.session.delete(report)
    db.session.commit()
    return {}, 204
