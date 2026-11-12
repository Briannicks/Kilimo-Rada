from sqlalchemy.exc import IntegrityError

from config import app, db
import models  # noqa: F401  (registers the tables)
from routes import register_routes
#connect api endpoints to flask
register_routes(app)

#check whether api endpoint is workin
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
# ---------- Error handlers (one place for the whole app) ----------
@app.errorhandler(ValueError)
def validation_error(error):
    """Any @validates error in models becomes a clean 422 response."""
    db.session.rollback()
    return {"error": str(error)}, 422


@app.errorhandler(IntegrityError)
def integrity_error(error):
    db.session.rollback()
    return {"error": "That record already exists or is linked to missing data"}, 409
@app.errorhandler(404)
def not_found(error):
    return {"error": "Not found"}, 404


@app.errorhandler(405)
def method_not_allowed(error):
    return {"error": "Method not allowed"}, 405


@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return {"error": "Something went wrong on the server"}, 500

if __name__ == "__main__":
    app.run(port=5555, debug=True)