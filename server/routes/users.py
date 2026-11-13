from flask import Blueprint, request
from rpds import List

from config import db
from helpers import get_data, paginate
from models import Broadcast, Farmer, MarketPrice, Report, User
from routes.auth import admin_required, current_user, login_required
from services import upload_image

bp = Blueprint("users", __name__)


@bp.get("/users")
@admin_required
def list_users():
    #List all staff accounts (admin only)
    
    return paginate(User.query.order_by(User.created_at.desc())), 200


@bp.patch("/users/<int:user_id>/role")
@admin_required
def change_role(user_id):
    #Make a user admin or officer (admin only)
   
    user = db.get_or_404(User, user_id)
    if user.id == current_user().id:
        return {"error": "You cannot change your own role"}, 400
    user.role = get_data().get("role")
    db.session.commit()
    return user.to_dict(), 200


@bp.patch("/users/me")
@login_required
def update_profile():
    #Update my name and/or avatar. Send JSON {name}, or form-data with 'name' and an 'avatar' file.

    user = current_user()
    data = request.form if (request.form or request.files) else get_data()

    if data.get("name"):
        user.name = data.get("name")
    if "avatar" in request.files:
        user.avatar_url = upload_image(request.files["avatar"])

    db.session.commit()
    return user.to_dict(), 200


@bp.get("/dashboard")
@login_required
def dashboard():
    #Numbers for the dashboard home page

    categories = {
        category: Report.query.filter_by(category=category).count()
        for category in Report.CATEGORIES
    }
    recent = Report.query.order_by(Report.created_at.desc()).limit(5).all()
    sms_sent = db.session.query(db.func.coalesce(db.func.sum(Broadcast.recipient_count), 0)).scalar()

    return {
        "total_farmers": Farmer.query.count(),
        "open_reports": Report.query.filter_by(status="open").count(),
        "resolved_reports": Report.query.filter_by(status="resolved").count(),
        "market_prices": MarketPrice.query.count(),
        "broadcasts_sent": Broadcast.query.count(),
        "sms_sent": int(sms_sent),
        "reports_by_category": categories,
        "recent_reports": [report.to_dict() for report in recent],
    }, 200