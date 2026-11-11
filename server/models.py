
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

