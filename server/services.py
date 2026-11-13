import os

from dotenv import load_dotenv

load_dotenv()  

import cloudinary.uploader  # noqa: E402
from sendgrid import SendGridAPIClient  # noqa: E402
from sendgrid.helpers.mail import Mail  # noqa: E402

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def send_email(to, subject, html):
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print(f"[DEV EMAIL] to={to} | {subject}\n{html}")
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
        print(f"Email failed: {error}")
        return False


def send_otp_email(to, code):
    html = (
        "<p>Your KilimoRada login code is:</p>"
        f"<h2 style='letter-spacing:4px'>{code}</h2>"
        "<p>It expires in 5 minutes. If you did not try to log in, ignore this email.</p>"
    )
    return send_email(to, "Your KilimoRada login code", html)


def upload_image(file, folder="kilimorada/avatars"):
    """file = request.files['image']. Returns the image URL."""
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
        print(f"[DEV UPLOAD] {file.filename}")
        return "https://via.placeholder.com/150"

    result = cloudinary.uploader.upload(file, folder=folder, resource_type="image")
    return result["secure_url"]


def send_sms(phone_numbers, message):
    print(f"[DEV SMS] to={phone_numbers} | {message}")
    return {"sent": len(phone_numbers), "failed": 0}