from sqlalchemy.exc import IntegrityError

from config import app, db
import models  # noqa: F401  (registers the tables)
from routes import register_routes
#connect api endpoints to flask
register_routes(app)
