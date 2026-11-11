
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import validates

from config import bcrypt, db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)



