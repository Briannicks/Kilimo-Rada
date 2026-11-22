"""External services used across the app: email (SendGrid), images (Cloudinary), SMS (Africa's Talking).
If an API key is missing, functions print instead of failing, so local dev still works."""
import json                                   # FIX: new import
import os

from dotenv import load_dotenv

load_dotenv()  # must run before importing cloudinary so it can read CLOUDINARY_URL

import cloudinary.uploader  # noqa: E402
import requests  # noqa: E402

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


# ---------- Email (SendGrid) ----------
# ---------- Email (Brevo HTTPS API: no domain needed, works on Render free) ----------
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to, subject, html):
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        print(f"[DEV EMAIL] to={to} | {subject}\n{html}", flush=True)
        return True
    try:
        response = requests.post(
            BREVO_URL,
            headers={"api-key": api_key, "accept": "application/json"},
            json={
                "sender": {
                    "name": os.environ.get("MAIL_FROM_NAME", "KilimoRada"),
                    "email": os.environ["MAIL_FROM"],  # the address you verified in Brevo
                },
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": html,
            },
            timeout=10,
        )
        if response.status_code >= 300:
            print(f"Email failed ({response.status_code}): {response.text}", flush=True)
            return False
        return True
    except requests.RequestException as error:
        print(f"Email failed: {error}", flush=True)
        return False

# ---------- KilimoRada emails (uses email_templates.py) ----------
import email_templates  # noqa: E402

OTP_MINUTES = 10


def send_verify_email(user, code):
    subject, html = email_templates.verify_email(user.name, code, OTP_MINUTES)
    return send_email(user.email, subject, html)


def send_otp_email(user, code):
    """Login 2FA code."""
    subject, html = email_templates.login_code(user.name, code, OTP_MINUTES)
    return send_email(user.email, subject, html)


def notify_admins_new_officer(officer):
    from models import User

    admins = User.query.filter_by(role="admin", is_approved=True).all()
    for admin in admins:
        subject, html = email_templates.new_officer_waiting(admin.name, officer)
        send_email(admin.email, subject, html)


def send_approved_email(user):
    subject, html = email_templates.account_approved(user.name)
    return send_email(user.email, subject, html)


def send_rejected_email(user):
    subject, html = email_templates.account_rejected(user.name)
    return send_email(user.email, subject, html)


# ---------- Images (Cloudinary) ----------
def upload_image(file, folder="kilimorada/avatars"):
    """file = request.files['avatar']. Returns the image URL."""
    if not file or not file.filename:
        raise ValueError("No image uploaded")

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Image must be png, jpg, jpeg or webp")

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise ValueError("Image must be smaller than 5 MB")

    if not os.environ.get("CLOUDINARY_URL"):
        print(f"[DEV UPLOAD] {file.filename}", flush=True)
        return "https://via.placeholder.com/150"

    result = cloudinary.uploader.upload(file, folder=folder, resource_type="image")
    return result["secure_url"]


# ---------- SMS (Africa's Talking) ----------   # FIX: everything below is rewritten
# Africa's Talking status codes that mean the message was accepted: Processed, Sent, Queued
SMS_OK_CODES = {"100", "101", "102"}


def _sms_failed(count, reason):
    print(f"SMS failed: {reason}", flush=True)
    return {"sent": 0, "failed": count, "error": reason}


def send_sms(phone_numbers, message):
    """Sends one SMS to a list of numbers like ['+254712345678'].
    Returns {"sent": n, "failed": n}, plus "error" when nothing could be sent.

    Sandbox note: with AT_USERNAME=sandbox, messages are NOT delivered to real phones.
    They only appear in the Africa's Talking simulator for the number you launched there.
    """
    from models import Farmer  # imported here to avoid a circular import

    # Same number format everywhere (0712... -> +254712...), no blanks, no duplicates
    numbers = list(dict.fromkeys(Farmer.normalize_phone(phone) for phone in phone_numbers if phone))
    if not numbers:
        return {"sent": 0, "failed": 0}

    # .strip(): a trailing space or newline pasted into a hosting dashboard breaks the request
    username = (os.environ.get("AT_USERNAME") or "sandbox").strip()
    api_key = (os.environ.get("AT_API_KEY") or "").strip()

    if not api_key:
        # For local dev without a key, put SMS_DRY_RUN=true in your .env
        if os.environ.get("SMS_DRY_RUN", "").strip().lower() == "true":
            print(f"[DRY RUN SMS] to={numbers} | {message}", flush=True)
            return {"sent": len(numbers), "failed": 0}
        # Report the truth instead of "sent": the dashboard must not say farmers were texted when they were not
        return _sms_failed(len(numbers), "AT_API_KEY is not set on the server, so no SMS can be sent")

    try:
        from africastalking.SMS import SMSService

        # A fresh client per call. africastalking.initialize() swaps module-level globals,
        # which is not safe when several USSD background threads send at the same time.
        response = SMSService(username, api_key).send(message, numbers)
    except Exception as error:
        return _sms_failed(len(numbers), f"{type(error).__name__}: {error} (username={username})")

    # The SDK only returns a dict when the reply's content-type is exactly "application/json".
    # Anything else (e.g. "application/json;charset=UTF-8") comes back as raw text, so parse it here.
    if isinstance(response, (str, bytes)):
        try:
            response = json.loads(response)
        except ValueError:
            return _sms_failed(len(numbers), f"Unexpected reply from Africa's Talking: {str(response)[:200]}")

    print(f"SMS response (username={username}): {response}", flush=True)
    data = response.get("SMSMessageData", {}) if isinstance(response, dict) else {}
    recipients = data.get("Recipients") or []
    if not recipients:
        return {"sent": 0, "failed": len(numbers), "error": data.get("Message") or "No recipients"}

    accepted = [
        r for r in recipients
        if r.get("status") == "Success" or str(r.get("statusCode")) in SMS_OK_CODES
    ]
    result = {"sent": len(accepted), "failed": len(numbers) - len(accepted)}
    if not accepted:
        result["error"] = recipients[0].get("status") or data.get("Message") or "Rejected"
    return result