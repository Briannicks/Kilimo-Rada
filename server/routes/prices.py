from flask import Blueprint, request

from config import db
from helpers import get_data, paginate
from models import MarketPrice
from routes.auth import current_user, login_required

bp = Blueprint("prices", __name__)

EDITABLE_FIELDS = ("crop", "market", "unit", "price")


def can_edit(price):
    #Only the person who posted a price (or an admin) can change it.
    user = current_user()
    return price.user_id == user.id or user.role == "admin"


@bp.get("/prices")
@login_required
def list_prices():
    #Market prices with filters and pagination

    query = MarketPrice.query
    crop = request.args.get("crop", "").strip()
    if crop:
        query = query.filter(MarketPrice.crop.ilike(crop))
    market = request.args.get("market", "").strip()
    if market:
        query = query.filter(MarketPrice.market.ilike(market))
    return paginate(query.order_by(MarketPrice.updated_at.desc())), 200


@bp.post("/prices")
@login_required
def create_price():
    #Post a new market price (you become its owner)

    data = get_data()
    price = MarketPrice(
        crop=data.get("crop"),
        market=data.get("market"),
        unit=data.get("unit"),
        price=data.get("price"),
        owner=current_user(),
    )
    db.session.add(price)
    db.session.commit()
    return price.to_dict(), 201


@bp.patch("/prices/<int:price_id>")
@login_required
def update_price(price_id):
    #Edit a price (owner or admin only)
   
    price = db.get_or_404(MarketPrice, price_id)
    if not can_edit(price):
        return {"error": "You can only edit prices you posted"}, 403

    data = get_data()
    for field in EDITABLE_FIELDS:
        if field in data:
            setattr(price, field, data[field])
    db.session.commit()
    return price.to_dict(), 200


@bp.delete("/prices/<int:price_id>")
@login_required
def delete_price(price_id):
    #Delete a price (owner or admin only)

    price = db.get_or_404(MarketPrice, price_id)
    if not can_edit(price):
        return {"error": "You can only delete prices you posted"}, 403
    db.session.delete(price)
    db.session.commit()
    return {}, 204
