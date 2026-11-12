from sqlalchemy.exc import IntegrityError

from config import app, db
import models  # noqa: F401  (registers the tables)
from routes import register_routes
#connect api endpoints to flask
register_routes(app)


@app.get("/api/health")
def health():
    """Health check
    ---
    tags: [Setup]
    responses:
      200:
        description: Server is running
    """
    return {"status": "ok"}, 200