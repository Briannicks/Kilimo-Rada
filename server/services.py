"""External services used across the app: email (SendGrid), images (Cloudinary), SMS (Africa's Talking).
If an API key is missing, functions print instead of failing, so local dev still works."""
import os

from dotenv import load_dotenv

load_dotenv()  # must run before importing cloudinary so it can read CLOUDINARY_URL

import cloudinary.uploader  # noqa: E402
from sendgrid import SendGridAPIClient  # noqa: E402
from sendgrid.helpers.mail import Mail  # noqa: E402

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


# ---------- Email (SendGrid) ----------
def send_email(to, subject, html):
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print(f"[DEV EMAIL] to={to} | {subject}\n{html}", flush=True)
        return True
    try:
        message = Mail(
            from_email=os.environ.get("MAIL_FROM", "no-reply@kilimorada.app"),
            to_emails=to,
            subject=subject,
            html_content=html,
        )
        SendGridAPIClient(api_key).send(message)
        return True
    except Exception as error:
        print(f"Email failed: {error}", flush=True)
        return False


def send_otp_email(to, code):
    """Used by the login route for 2FA."""
    html = (
        "<p>Your KilimoRada login code is:</p>"
        f"<h2 style='letter-spacing:4px'>{code}</h2>"
        "<p>It expires in 5 minutes. If you did not try to log in, ignore this email.</p>"
    )
    return send_email(to, "Your KilimoRada login code", html)


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