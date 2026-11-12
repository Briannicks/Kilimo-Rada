from functools import wraps

from flask import Blueprint, current_app, session

from config import db
from helpers import get_data
from models import User
from services import send_otp_email

bp = Blueprint("auth", __name__)

MAX_OTP_ATTEMPTS = 5


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


def start_session(user):
    session.clear()
    session["user_id"] = user.id
    session.permanent = True


def mask_email(email):
    name, domain = email.split("@")
    return f"{name[0]}***@{domain}"


def send_new_code(user):
    code = user.generate_otp()
    db.session.commit()
    send_otp_email(user.email, code)
    session["otp_attempts"] = 0


# ---------- routes ----------
@bp.post("/signup")
def signup():
    """Create an account (the very first user becomes admin)
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          example: {name: Jane Wanjiru, email: jane@example.com, password: password123}
    responses:
      201: {description: Account created and logged in}
      409: {description: Email already registered}
      422: {description: Invalid data}
    """
    data = get_data()
    email = (data.get("email") or "").strip().lower()
    if User.query.filter_by(email=email).first():
        return {"error": "Email already registered"}, 409

    role = "admin" if User.query.count() == 0 else "officer"
    user = User(name=data.get("name"), email=email, role=role)
    user.password = data.get("password")
    db.session.add(user)
    db.session.commit()

    start_session(user)
    return user.to_dict(), 201


@bp.post("/login")
def login():
    """Step 1 of login: check password, then email a 6-digit code
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          example: {email: admin@kilimorada.app, password: password123}
    responses:
      200: {description: Code sent (or logged in if 2FA is off)}
      401: {description: Wrong email or password}
    """
    data = get_data()
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not user.authenticate(data.get("password") or ""):
        return {"error": "Invalid email or password"}, 401

    if not current_app.config["TWO_FACTOR_ENABLED"]:
        start_session(user)
        return user.to_dict(), 200

    session.clear()
    session["pending_user_id"] = user.id
    send_new_code(user)
    return {
        "two_factor_required": True,
        "message": f"We sent a 6-digit code to {mask_email(user.email)}",
    }, 200


@bp.post("/verify-otp")
def verify_otp():
    """Step 2 of login: check the emailed code and start the session
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          example: {code: "123456"}
    responses:
      200: {description: Logged in}
      401: {description: Wrong or expired code}
      429: {description: Too many attempts}
    """
    user_id = session.get("pending_user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return {"error": "Please log in first"}, 401

    attempts = session.get("otp_attempts", 0)
    if attempts >= MAX_OTP_ATTEMPTS:
        session.clear()
        return {"error": "Too many wrong codes. Please log in again."}, 429

    if not user.verify_otp(get_data().get("code", "")):
        session["otp_attempts"] = attempts + 1
        return {"error": "Invalid or expired code"}, 401

    db.session.commit()
    start_session(user)
    return user.to_dict(), 200


@bp.post("/resend-otp")
def resend_otp():
    """Send a new login code
    ---
    tags: [Auth]
    responses:
      200: {description: New code sent}
      401: {description: No login in progress}
    """
    user_id = session.get("pending_user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return {"error": "Please log in first"}, 401
    send_new_code(user)
    return {"message": f"New code sent to {mask_email(user.email)}"}, 200


@bp.get("/me")
def me():
    """Current logged-in user (frontend calls this on page load)
    ---
    tags: [Auth]
    responses:
      200: {description: The logged-in user}
      401: {description: Not logged in}
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
      204: {description: Logged out}
    """
    session.clear()
    return {}, 204