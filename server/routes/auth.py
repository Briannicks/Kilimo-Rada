from functools import wraps

from flask import Blueprint, session

from config import db
from models import User

bp = Blueprint("auth", __name__)


# ---------- helpers everyone imports ----------
def current_user():
    """Returns the logged-in User, or None."""
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return {"error": "Please log in"}, 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return {"error": "Please log in"}, 401
        if user.role != "admin":
            return {"error": "Admins only"}, 403
        return fn(*args, **kwargs)
    return wrapper



@bp.get("/me")
def me():
    """Current logged-in user (frontend calls this on page load)
    ---
    tags: [Auth]
    responses:
      200:
        description: The logged-in user
      401:
        description: Not logged in
    """
    user = current_user()
    if not user:
        return {"error": "Not logged in"}, 401
    return user.to_dict(), 200


@bp.delete("/logout")
def logout():
    """Log out
    ---
    tags: [Auth]
    responses:
      204:
        description: Logged out
    """
    session.clear()
    return {}, 204