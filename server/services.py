"""External services used across the app: email (SendGrid), images (Cloudinary), SMS (Africa's Talking).
If an API key is missing, functions print instead of failing, so local dev still works."""
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


# ---------- SMS (Africa's Talking) ----------
def send_sms(phone_numbers, message):
    """Sends one SMS to a list of numbers like ['+254712345678']."""
    phone_numbers = [phone for phone in phone_numbers if phone]
    if not phone_numbers:
        return {"sent": 0, "failed": 0}

    username = os.environ.get("AT_USERNAME", "sandbox")
    api_key = os.environ.get("AT_API_KEY")
    if not api_key:
        print(f"[DEV SMS] AT_API_KEY not set, SMS NOT sent. to={phone_numbers} | {message}", flush=True)
        return {"sent": len(phone_numbers), "failed": 0}

    try:
        import africastalking

        africastalking.initialize(username, api_key)
        response = africastalking.SMS.send(message, phone_numbers)
        print(f"SMS response (username={username}): {response}", flush=True)

        data = response.get("SMSMessageData", {})
        recipients = data.get("Recipients", [])
        if not recipients:
            return {"sent": 0, "failed": len(phone_numbers), "error": data.get("Message", "No recipients")}
        sent = sum(1 for recipient in recipients if recipient.get("status") == "Success")
        return {"sent": sent, "failed": len(recipients) - sent}
    except Exception as error:
        print(f"SMS failed (username={username}): {error}", flush=True)
        return {"sent": 0, "failed": len(phone_numbers), "error": str(error)}