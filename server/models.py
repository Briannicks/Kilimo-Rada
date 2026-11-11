
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import validates  # type: ignore[reportMissingImports]

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
        self.otp_hash = None          
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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "ward": self.ward,
            "main_crop": self.main_crop,
            "registered_via": self.registered_via,
            "added_by_id": self.added_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

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

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "reply": self.reply,
            "replied_by": self.replied_by.name if self.replied_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "farmer": {
                "id": self.farmer.id,
                "name": self.farmer.name,
                "phone": self.farmer.phone,
                "ward": self.farmer.ward,
            } if self.farmer else None,
        }


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
        value = int(value)
        if value <= 0:
            raise ValueError("Price must be greater than 0")


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

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "target_crop": self.target_crop or "All farmers",
            "recipient_count": self.recipient_count,
            "sender": self.sender.name if self.sender else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


