import time
from functools import wraps

from flask import Blueprint, current_app, request, session

from config import db
from models import User
from schemas.auth_schemas import LoginSchema, SignupSchema, VerifyCodeSchema, user_schema
from services import (
    OTP_MINUTES,
    notify_admins_new_officer,
    send_otp_email,
    send_verify_email,
)

bp = Blueprint("auth", __name__)

MAX_CODE_ATTEMPTS = 5
RESEND_WAIT_SECONDS = 30


# ---------- helpers everyone imports ----------
def current_user():
    """Returns the logged-in User, or None."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if user and not user.is_approved:
        return None
    return user


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


def mask_email(email):
    """brian@gmail.com -> b****@gmail.com"""
    name, _, domain = email.partition("@")
    return f"{name[0]}{'*' * max(len(name) - 1, 3)}@{domain}"


def start_code_step(user, purpose):
    """Emails a new code and remembers who is in the middle of verifying.
    purpose: "signup" (verify email) or "login" (2FA)."""
    code = user.generate_otp(minutes=OTP_MINUTES)
    db.session.commit()
    session.clear()
    session["pending_user_id"] = user.id
    session["otp_purpose"] = purpose
    session["otp_attempts"] = 0
    session["otp_sent_at"] = time.time()
    if purpose == "signup":
        send_verify_email(user, code)
    else:
        send_otp_email(user, code)
    return f"We sent a 6-digit code to {mask_email(user.email)}"


def finish_login(user):
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    return user_schema.dump(user), 200


PENDING_MESSAGE = "Your account is waiting for admin approval. We'll email you once it's approved."


# ---------- routes ----------
@bp.post("/signup")
def signup():
    """Create an officer account. Sends an email verification code.
    The first account ever created becomes the admin (approved automatically).
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [name, email, password, county, ward]
          properties:
            name: {type: string, example: Jane Wanjiku}
            email: {type: string, example: jane@example.com}
            password: {type: string, example: strongpass123}
            county: {type: string, example: Nakuru}
            ward: {type: string, example: Tinet}
    responses:
      201:
        description: "{ verification_required: true, message }"
      409:
        description: Email already registered
      422:
        description: Invalid fields
    """
    data = SignupSchema().load(request.get_json() or {})

    if User.query.filter_by(email=data["email"].lower()).first():
        return {"error": "An account with this email already exists. Please log in."}, 409

    is_first_user = User.query.count() == 0
    user = User(
        name=data["name"],
        email=data["email"],
        county=data["county"],
        ward=data["ward"],
        role="admin" if is_first_user else "officer",
        is_email_verified=False,
        is_approved=is_first_user,
    )
    user.password = data["password"]
    db.session.add(user)
    db.session.commit()

    message = start_code_step(user, "signup")
    return {"verification_required": True, "message": message}, 201


@bp.post("/login")
def login():
    """Step 1 of login: email + password
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string}
            password: {type: string}
    responses:
      200:
        description: "{ two_factor_required: true } or { verification_required: true } or the user"
      401:
        description: Wrong email or password
      403:
        description: "{ pending_approval: true } account not approved yet"
    """
    data = LoginSchema().load(request.get_json() or {})
    user = User.query.filter_by(email=data["email"].lower()).first()
    if not user or not user.authenticate(data["password"]):
        return {"error": "Wrong email or password"}, 401

    if not user.is_email_verified:
        message = start_code_step(user, "signup")
        return {"verification_required": True, "message": message}, 200

    if not user.is_approved:
        session.clear()
        return {"error": PENDING_MESSAGE, "pending_approval": True}, 403

    if current_app.config.get("TWO_FACTOR_ENABLED", True):
        message = start_code_step(user, "login")
        return {"two_factor_required": True, "message": message}, 200

    return finish_login(user)


@bp.post("/verify-otp")
def verify_otp():
    """Step 2: check the emailed 6-digit code (email verification or login)
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [code]
          properties:
            code: {type: string, example: "123456"}
    responses:
      200:
        description: "The user (logged in), or { pending_approval: true, message }"
      401:
        description: Wrong or expired code / session expired
      429:
        description: Too many wrong attempts
    """
    user_id = session.get("pending_user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return {"error": "Your session expired. Please log in again."}, 401

    if session.get("otp_attempts", 0) >= MAX_CODE_ATTEMPTS:
        session.clear()
        return {"error": "Too many wrong codes. Please log in again."}, 429

    data = VerifyCodeSchema().load(request.get_json() or {})
    if not user.verify_otp(data["code"]):
        session["otp_attempts"] = session.get("otp_attempts", 0) + 1
        return {"error": "Wrong or expired code"}, 401

    purpose = session.get("otp_purpose", "login")

    if purpose == "signup":
        user.is_email_verified = True
        db.session.commit()
        if user.is_approved:  # the first admin goes straight in
            return finish_login(user)
        notify_admins_new_officer(user)
        session.clear()
        return {"pending_approval": True, "message": "Email verified. " + PENDING_MESSAGE}, 200

    db.session.commit()  # saves that the code was used
    if not user.is_approved:
        session.clear()
        return {"error": PENDING_MESSAGE, "pending_approval": True}, 403
    return finish_login(user)


@bp.post("/resend-otp")
def resend_otp():
    """Send a new code (works for email verification and login)
    ---
    tags: [Auth]
    responses:
      200:
        description: "{ message }"
      401:
        description: Session expired
      429:
        description: Asked too soon (wait 30 seconds)
    """
    user_id = session.get("pending_user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return {"error": "Your session expired. Please log in again."}, 401

    waited = time.time() - session.get("otp_sent_at", 0)
    if waited < RESEND_WAIT_SECONDS:
        seconds = int(RESEND_WAIT_SECONDS - waited) + 1
        return {"error": f"Please wait {seconds} seconds before asking for a new code."}, 429

    message = start_code_step(user, session.get("otp_purpose", "login"))
    return {"message": message}, 200


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
    return user_schema.dump(user), 200


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