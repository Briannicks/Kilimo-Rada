from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import MarketPrice
from routes.auth import current_user, login_required
from schemas.report_schemas import price_schema

bp = Blueprint("prices", __name__)


def can_edit(price):
    """Only the person who posted a price (or an admin) can change it."""
    user = current_user()
    return price.user_id == user.id or user.role == "admin"


@bp.get("/prices")
@login_required
def list_prices():
    """Market prices with filters and pagination
    ---
    tags: [Market Prices]
    parameters:
      - {name: crop, in: query, type: string}
      - {name: market, in: query, type: string}
      - {name: page, in: query, type: integer}
      - {name: per_page, in: query, type: integer}
    responses:
      200: {description: Paginated prices}
    """
    query = MarketPrice.query
    crop = request.args.get("crop", "").strip()
    if crop:
        query = query.filter(MarketPrice.crop.ilike(crop))
    market = request.args.get("market", "").strip()
    if market:
        query = query.filter(MarketPrice.market.ilike(market))
    return paginate(query.order_by(MarketPrice.updated_at.desc()), price_schema), 200


@bp.post("/prices")
@login_required
def create_price():
    """Post a new market price (you become its owner)
    ---
    tags: [Market Prices]
    parameters:
      - in: body
        name: body
        schema:
          example: {crop: Maize, market: Nakuru, unit: 90kg bag, price: 3800}
    responses:
      201: {description: Price created}
      422: {description: Invalid data}
    """
    data = price_schema.load(get_data())
    price = MarketPrice(**data, owner=current_user())
    db.session.add(price)
    db.session.commit()
    return price_schema.dump(price), 201


@bp.patch("/prices/<int:price_id>")
@login_required
def update_price(price_id):
    """Edit a price (owner or admin only)
    ---
    tags: [Market Prices]
    parameters:
      - {name: price_id, in: path, type: integer, required: true}
      - in: body
        name: body
        schema:
          example: {price: 4000}
    responses:
      200: {description: Updated}
      403: {description: Not your price}
    """
    price = db.get_or_404(MarketPrice, price_id)
    if not can_edit(price):
        return {"error": "You can only edit prices you posted"}, 403

    for field, value in price_schema.load(get_data(), partial=True).items():
        setattr(price, field, value)
    db.session.commit()
    return price_schema.dump(price), 200


@bp.delete("/prices/<int:price_id>")
@login_required
def delete_price(price_id):
    """Delete a price (owner or admin only)
    ---
    tags: [Market Prices]
    parameters:
      - {name: price_id, in: path, type: integer, required: true}
    responses:
      204: {description: Deleted}
      403: {description: Not your price}
    """
    price = db.get_or_404(MarketPrice, price_id)
    if not can_edit(price):
        return {"error": "You can only delete prices you posted"}, 403
    db.session.delete(price)
    db.session.commit()
    return {}, 204