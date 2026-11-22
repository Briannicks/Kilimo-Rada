from flask import Blueprint, request

from config import db
from models import Broadcast, Farmer, MarketPrice, Report, User          # FIX: added Broadcast, Farmer, MarketPrice, Report
from routes.auth import admin_required, current_user, login_required
from schemas.auth_schemas import ProfileUpdateSchema, RoleSchema, user_schema, users_schema
from schemas.report_schemas import report_schema                          # FIX: new import
from services import send_approved_email, send_rejected_email, upload_image

bp = Blueprint("users", __name__)


def get_user_or_404(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None, ({"error": "User not found"}, 404)
    return user, None


@bp.get("/users")
@admin_required
def list_users():
    """List staff accounts (admin only)
    ---
    tags: [Users]
    parameters:
      - {in: query, name: status, type: string, enum: [pending, active], description: "pending = verified email, waiting for approval"}
      - {in: query, name: role, type: string, enum: [admin, officer]}
      - {in: query, name: search, type: string, description: Name or email}
      - {in: query, name: county, type: string}
      - {in: query, name: page, type: integer}
      - {in: query, name: per_page, type: integer}
    responses:
      200:
        description: "{ items, page, per_page, total, pages }"
    """
    query = User.query

    status = request.args.get("status")
    if status == "pending":
        query = query.filter(User.is_approved.is_(False), User.is_email_verified.is_(True))
    elif status == "active":
        query = query.filter(User.is_approved.is_(True))

    role = request.args.get("role")
    if role:
        query = query.filter(User.role == role)

    county = request.args.get("county")
    if county:
        query = query.filter(User.county == county)

    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 50)
    result = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return {
        "items": users_schema.dump(result.items),
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    }, 200


@bp.patch("/users/<int:user_id>/approve")
@admin_required
def approve_user(user_id):
    """Approve an officer who is waiting (admin only). Emails them.
    ---
    tags: [Users]
    parameters:
      - {in: path, name: user_id, type: integer, required: true}
    responses:
      200:
        description: The approved user
      400:
        description: Email not verified yet, or already approved
      404:
        description: User not found
    """
    user, error = get_user_or_404(user_id)
    if error:
        return error
    if user.is_approved:
        return {"error": "This account is already approved"}, 400
    if not user.is_email_verified:
        return {"error": "This person has not verified their email yet"}, 400

    user.is_approved = True
    db.session.commit()
    send_approved_email(user)
    return user_schema.dump(user), 200


@bp.delete("/users/<int:user_id>/reject")
@admin_required
def reject_user(user_id):
    """Reject an officer who is waiting (admin only). Deletes the signup and emails them.
    ---
    tags: [Users]
    parameters:
      - {in: path, name: user_id, type: integer, required: true}
    responses:
      204:
        description: Rejected and removed
      400:
        description: Account is already approved
      404:
        description: User not found
    """
    user, error = get_user_or_404(user_id)
    if error:
        return error
    if user.is_approved:
        return {"error": "Approved accounts can't be rejected"}, 400

    send_rejected_email(user)
    db.session.delete(user)
    db.session.commit()
    return {}, 204


@bp.patch("/users/<int:user_id>/role")
@admin_required
def change_role(user_id):
    """Change a user's role (admin only). You can't change your own role.
    ---
    tags: [Users]
    parameters:
      - {in: path, name: user_id, type: integer, required: true}
      - in: body
        name: body
        schema:
          type: object
          required: [role]
          properties:
            role: {type: string, enum: [admin, officer]}
    responses:
      200:
        description: The updated user
      400:
        description: Tried to change own role, or account not approved
    """
    user, error = get_user_or_404(user_id)
    if error:
        return error
    if user.id == current_user().id:
        return {"error": "You can't change your own role"}, 400
    if not user.is_approved:
        return {"error": "Approve this account first"}, 400

    data = RoleSchema().load(request.get_json() or {})
    user.role = data["role"]
    db.session.commit()
    return user_schema.dump(user), 200


@bp.patch("/users/me")
@login_required
def update_me():
    """Update my name, county, ward and/or profile picture
    ---
    tags: [Users]
    consumes: [application/json, multipart/form-data]
    parameters:
      - {in: formData, name: name, type: string}
      - {in: formData, name: county, type: string}
      - {in: formData, name: ward, type: string}
      - {in: formData, name: avatar, type: file, description: "png, jpg, jpeg or webp, max 5 MB"}
    responses:
      200:
        description: The updated user
    """
    user = current_user()

    if request.content_type and request.content_type.startswith("multipart/form-data"):
        raw = request.form.to_dict()
    else:
        raw = request.get_json() or {}
    data = ProfileUpdateSchema().load(raw)

    for field in ("name", "county", "ward"):
        if field in data:
            setattr(user, field, data[field])

    avatar = request.files.get("avatar")
    if avatar:
        user.avatar_url = upload_image(avatar)

    db.session.commit()
    return user_schema.dump(user), 200


# FIX: NEW ROUTE. The frontend Dashboard calls GET /api/dashboard, which did not exist (404 "Not found").
@bp.get("/dashboard")
@login_required
def dashboard():
    """Numbers for the dashboard home page
    ---
    tags: [Dashboard]
    responses:
      200:
        description: Counts, reports by category and the 5 newest reports
    """
    by_status = dict(db.session.query(Report.status, db.func.count(Report.id)).group_by(Report.status).all())
    by_category = dict(db.session.query(Report.category, db.func.count(Report.id)).group_by(Report.category).all())
    recent = Report.query.order_by(Report.created_at.desc(), Report.id.desc()).limit(5).all()

    # The app keeps no SMS log, so "SMS sent" counts what the dashboard itself sends:
    # every broadcast recipient plus every reply an officer sent to a farmer.
    broadcast_sms = db.session.query(db.func.coalesce(db.func.sum(Broadcast.recipient_count), 0)).scalar()
    reply_sms = Report.query.filter(Report.replied_by_id.isnot(None)).count()

    return {
        "total_farmers": Farmer.query.count(),
        "open_reports": by_status.get("open", 0),
        "resolved_reports": by_status.get("resolved", 0),
        "market_prices": MarketPrice.query.count(),
        "broadcasts_sent": Broadcast.query.count(),
        "sms_sent": int(broadcast_sms) + reply_sms,
        "reports_by_category": {name: by_category.get(name, 0) for name in Report.CATEGORIES},
        "recent_reports": report_schema.dump(recent, many=True),
    }, 200