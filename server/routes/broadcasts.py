from flask import Blueprint

from config import db
from helpers import get_data, paginate
from models import Broadcast, Farmer
from routes.auth import current_user, login_required
from schemas.ussd_schemas import broadcast_schema
from services import send_sms

bp = Blueprint("broadcasts", __name__)


@bp.get("/broadcasts")
@login_required
def list_broadcasts():
    """Broadcast history
    ---
    tags: [Broadcasts]
    parameters:
      - {name: page, in: query, type: integer}
      - {name: per_page, in: query, type: integer}
    responses:
      200: {description: Paginated broadcasts}
    """
    return paginate(Broadcast.query.order_by(Broadcast.created_at.desc()), broadcast_schema), 200


@bp.post("/broadcasts")
@login_required
def send_broadcast():
    """Send an SMS to all farmers, or only farmers growing one crop
    ---
    tags: [Broadcasts]
    parameters:
      - in: body
        name: body
        schema:
          example: {message: Fall armyworm alert. Inspect your maize this week., target_crop: Maize}
    responses:
      201: {description: Broadcast sent}
      400: {description: No farmers match}
      422: {description: Message empty or over 160 characters}
    """
    # The schema checks the message (1-160 characters) BEFORE any SMS goes out
    data = broadcast_schema.load(get_data())
    target_crop = data.get("target_crop") or None
    broadcast = Broadcast(message=data["message"], target_crop=target_crop)

    query = Farmer.query
    if target_crop:
        query = query.filter(Farmer.main_crop.ilike(target_crop))
    phones = [farmer.phone for farmer in query.all()]
    if not phones:
        return {"error": "No farmers match this audience"}, 400

    result = send_sms(phones, broadcast.message)
    broadcast.recipient_count = result["sent"]
    broadcast.sender = current_user()
    db.session.add(broadcast)
    db.session.commit()

    response = broadcast_schema.dump(broadcast)
    response["sms"] = result
    return response, 201
