from config import app, db
from models import Broadcast, Farmer, MarketPrice, Report, User

with app.app_context():
    print("Clearing old data...")
    Broadcast.query.delete()
    Report.query.delete()
    MarketPrice.query.delete()
    Farmer.query.delete()
    User.query.delete()
    print("Creating users...")
    admin = User(name="Admin Officer", email="admin@kilimorada.app", role="admin")
    admin.password = "password123"
    officer = User(name="Field Officer", email="officer@kilimorada.app", role="officer")
    officer.password = "password123"
    db.session.add_all([admin, officer])
    db.session.commit()