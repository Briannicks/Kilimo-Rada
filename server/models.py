"""All KilimoRada models.
Each person writes ONLY inside their own section to avoid merge conflicts."""
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import validates

from config import bcrypt, db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)



