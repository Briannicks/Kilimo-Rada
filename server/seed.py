from config import app, db
from models import Broadcast, Farmer, MarketPrice, Report, User

with app.app_context():
    print("Clearing old data...")
    Broadcast.query.delete()
    Report.query.delete()
    MarketPrice.query.delete()
    Farmer.query.delete()
    User.query.delete()