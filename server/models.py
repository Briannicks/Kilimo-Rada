"""All KilimoRada models.
Each person writes ONLY inside their own section to avoid merge conflicts."""
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import validates

from config import bcrypt, db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)



class User(db.Model):
    __tablename__ = "users"

    ROLES = ("admin", "officer")

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="officer")
    avatar_url = db.Column(db.String(255))
    otp_hash = db.Column(db.String(128))
    otp_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)

   
    @property
    def password(self):
        raise AttributeError("Password is write-only")

    @password.setter
    def password(self, plain_password):
        if not plain_password or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = bcrypt.generate_password_hash(plain_password).decode("utf-8")

    def authenticate(self, plain_password):
        return bcrypt.check_password_hash(self.password_hash, plain_password)

   
    def generate_otp(self, minutes=5):
        """Creates a 6-digit code, stores only its hash, returns the plain code to email."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.otp_hash = bcrypt.generate_password_hash(code).decode("utf-8")
        self.otp_expires_at = utcnow() + timedelta(minutes=minutes)
        return code

    def verify_otp(self, code):
        if not self.otp_hash or not self.otp_expires_at:
            return False
        if utcnow() > self.otp_expires_at:
            return False
        if not bcrypt.check_password_hash(self.otp_hash, str(code).strip()):
            return False
        self.otp_hash = None          # a code can only be used once
        self.otp_expires_at = None
        return True

    
    @validates("name")
    def validate_name(self, key, value):
        value = (value or "").strip()
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters")
        return value

    @validates("email")
    def validate_email(self, key, value):
        value = (value or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            raise ValueError("Invalid email address")
        return value

    @validates("role")
    def validate_role(self, key, value):
        if value not in self.ROLES:
            raise ValueError(f"Role must be one of {self.ROLES}")
        return value



class Farmer(db.Model):
    __tablename__ = "farmers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    ward = db.Column(db.String(100))
    main_crop = db.Column(db.String(50))
    registered_via = db.Column(db.String(10), nullable=False, default="web")
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # null = self-registered on USSD
    created_at = db.Column(db.DateTime, default=utcnow)

    added_by = db.relationship("User", backref="farmers_added")

    @staticmethod
    def normalize_phone(phone):
        """Turns 0712345678 / 254712345678 / +254 712 345 678 into +254712345678."""
        phone = re.sub(r"[\s\-]", "", phone or "")
        if phone.startswith("0"):
            phone = "+254" + phone[1:]
        elif phone.startswith("254"):
            phone = "+" + phone
        return phone

    @validates("phone")
    def validate_phone(self, key, value):
        value = self.normalize_phone(value)
        if not re.match(r"^\+254[17]\d{8}$", value):
            raise ValueError("Phone must be a valid Kenyan number, e.g. 0712345678")
        return value

    @validates("name")
    def validate_name(self, key, value):
        value = (value or "").strip()
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters")
        return value

    @validates("ward", "main_crop")
    def clean_text(self, key, value):
        return value.strip().title() if value else None

    @validates("registered_via")
    def validate_registered_via(self, key, value):
        if value not in ("ussd", "web"):
            raise ValueError("registered_via must be 'ussd' or 'web'")
        return value



class Report(db.Model):
    __tablename__ = "reports"

    CATEGORIES = ("pest", "disease", "weather", "other")
    STATUSES = ("open", "resolved")

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("farmers.id"), nullable=False)
    category = db.Column(db.String(20), nullable=False, default="other")
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    reply = db.Column(db.Text)
    replied_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    farmer = db.relationship(
        "Farmer", backref=db.backref("reports", cascade="all, delete-orphan")
    )
    replied_by = db.relationship("User", backref="replies")

    @validates("category")
    def validate_category(self, key, value):
        value = (value or "other").lower()
        if value not in self.CATEGORIES:
            raise ValueError(f"Category must be one of {self.CATEGORIES}")
        return value

    @validates("status")
    def validate_status(self, key, value):
        if value not in self.STATUSES:
            raise ValueError(f"Status must be one of {self.STATUSES}")
        return value

    @validates("description")
    def validate_description(self, key, value):
        value = (value or "").strip()
        if len(value) < 3:
            raise ValueError("Description is too short")
        return value


class MarketPrice(db.Model):
    __tablename__ = "market_prices"

    id = db.Column(db.Integer, primary_key=True)
    crop = db.Column(db.String(50), nullable=False)
    market = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # KES
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # owner
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    owner = db.relationship("User", backref="prices")

    @validates("crop", "market")
    def validate_names(self, key, value):
        value = (value or "").strip().title()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    @validates("unit")
    def validate_unit(self, key, value):
        value = (value or "").strip()
        if not value:
            raise ValueError("unit is required, e.g. '90kg bag'")
        return value

    @validates("price")
    def validate_price(self, key, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError("Price must be a whole number in KES")
        if value <= 0:
            raise ValueError("Price must be greater than 0")
        return value



class Broadcast(db.Model):
    __tablename__ = "broadcasts"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(160), nullable=False)
    target_crop = db.Column(db.String(50))  # None = all farmers
    recipient_count = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # sender
    created_at = db.Column(db.DateTime, default=utcnow)

    sender = db.relationship("User", backref="broadcasts")

    @validates("message")
    def validate_message(self, key, value):
        value = (value or "").strip()
        if not value:
            raise ValueError("Message cannot be empty")
        if len(value) > 160:
            raise ValueError("Message must be 160 characters or less (1 SMS)")
        return value

    @validates("target_crop")
    def clean_crop(self, key, value):
        return value.strip().title() if value else None


def mask_phone(phone):
    """+254712345678 -> +25471***678 (privacy on the dashboard)."""
    return f"{phone[:6]}***{phone[-3:]}" if phone and len(phone) > 9 else phone


class UssdProfile(db.Model):
    """Remembers each phone's language choice (English / Kiswahili)."""
    __tablename__ = "ussd_profiles"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    language = db.Column(db.String(2), nullable=False, default="en")
    created_at = db.Column(db.DateTime, default=utcnow)

    @validates("language")
    def validate_language(self, key, value):
        if value not in ("en", "sw"):
            raise ValueError("Language must be 'en' or 'sw'")
        return value


class AiQuestion(db.Model):
    """Questions farmers ask the AI expert on USSD (option 5)."""
    __tablename__ = "ai_questions"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    question = db.Column(db.String(80), nullable=False)
    answer = db.Column(db.Text)
    language = db.Column(db.String(2), default="en")
    created_at = db.Column(db.DateTime, default=utcnow)


class InputReport(db.Model):
    """Farmer reports of fake batch codes or scam phone numbers (option 8)."""
    __tablename__ = "input_reports"

    KINDS = ("batch_code", "scam_number")

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(10), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)  # who reported
    kind = db.Column(db.String(20), nullable=False)
    value = db.Column(db.String(50), nullable=False)  # the code or number reported
    created_at = db.Column(db.DateTime, default=utcnow)

    @validates("kind")
    def validate_kind(self, key, value):
        if value not in self.KINDS:
            raise ValueError(f"kind must be one of {self.KINDS}")
        return value

    @validates("value")
    def validate_value(self, key, value):
        value = (value or "").strip().upper()
        if len(value) < 3:
            raise ValueError("Code or number is too short")
        return value


class VerifiedProduct(db.Model):
    """Official batch code registry, entered by admins from KEPHIS / PCPB / manufacturer records."""
    __tablename__ = "verified_products"

    STATUSES = ("genuine", "fake")

    id = db.Column(db.Integer, primary_key=True)
    batch_code = db.Column(db.String(50), unique=True, nullable=False)
    product = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="genuine")
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    added_by = db.relationship("User", backref="products_added")

    @validates("batch_code")
    def validate_code(self, key, value):
        value = re.sub(r"\s", "", value or "").upper()
        if len(value) < 3:
            raise ValueError("Batch code is too short")
        return value

    @validates("product", "manufacturer")
    def validate_text(self, key, value):
        value = (value or "").strip()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    @validates("status")
    def validate_status(self, key, value):
        if value not in self.STATUSES:
            raise ValueError(f"Status must be one of {self.STATUSES}")
        return value


class Agrovet(db.Model):
    """Agrovet shops an admin has verified (option 7)."""
    __tablename__ = "agrovets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ward = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    license_no = db.Column(db.String(50))
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    added_by = db.relationship("User", backref="agrovets_added")

    @validates("name", "ward")
    def validate_text(self, key, value):
        value = (value or "").strip().title()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    @validates("phone")
    def validate_phone(self, key, value):
        value = Farmer.normalize_phone(value)
        if not re.match(r"^\+254[17]\d{8}$", value):
            raise ValueError("Phone must be a valid Kenyan number, e.g. 0712345678")
        return value