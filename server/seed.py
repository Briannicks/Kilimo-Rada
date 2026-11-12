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
    print("Creating farmers...")
    farmer_data = [
        ("John Kiprop", "0712000001", "Tinet", "Maize"),
        ("Mary Chebet", "0712000002", "Tinet", "Beans"),
        ("Peter Mwangi", "0712000003", "Lanet", "Potatoes"),
        ("Grace Wanjiku", "0712000004", "Lanet", "Maize"),
        ("David Otieno", "0712000005", "Kuresoi", "Tea"),
        ("Faith Jeptoo", "0712000006", "Kuresoi", "Maize"),
        ("Samuel Kibet", "0712000007", "Molo", "Potatoes"),
        ("Esther Njeri", "0712000008", "Molo", "Beans"),
        ("Joseph Langat", "0712000009", "Tinet", "Avocado"),
        ("Ann Wambui", "0712000010", "Lanet", "Maize"),
    ]
    farmers = []
    for i, (name, phone, ward, crop) in enumerate(farmer_data):
        via = "ussd" if i % 2 == 0 else "web"
        farmers.append(Farmer(
            name=name, phone=phone, ward=ward, main_crop=crop,
            registered_via=via, added_by=None if via == "ussd" else officer,
        ))
    db.session.add_all(farmers)
    db.session.commit()
    print("Creating reports...")
    reports = [
        Report(farmer=farmers[0], category="pest", description="Fall armyworm on young maize"),
        Report(farmer=farmers[1], category="disease", description="Bean leaves turning yellow"),
        Report(farmer=farmers[2], category="disease", description="Potato blight after heavy rain"),
        Report(farmer=farmers[4], category="weather", description="Hailstorm damaged tea bushes"),
        Report(farmer=farmers[5], category="pest", description="Stalk borer in maize"),
        Report(farmer=farmers[7], category="other", description="Where can I buy certified bean seed?",
               status="resolved", reply="Visit the KALRO office in Njoro.", replied_by=officer),
    ]
    db.session.add_all(reports)
    print("Creating market prices...")
    prices = [
        MarketPrice(crop="Maize", market="Nakuru", unit="90kg bag", price=3800, owner=admin),
        MarketPrice(crop="Maize", market="Eldoret", unit="90kg bag", price=3600, owner=officer),
        MarketPrice(crop="Beans", market="Nakuru", unit="90kg bag", price=9500, owner=officer),
        MarketPrice(crop="Potatoes", market="Molo", unit="50kg bag", price=2200, owner=admin),
        MarketPrice(crop="Avocado", market="Nakuru", unit="kg", price=60, owner=officer),
    ]
    db.session.add_all(prices)
    print("Creating broadcasts...")
    db.session.add_all([
        Broadcast(message="Fall armyworm reported in Tinet. Inspect your maize this week.",
                  target_crop="Maize", recipient_count=4, sender=admin),
        Broadcast(message="Heavy rains expected. Clear drainage around your farms.",
                  recipient_count=10, sender=officer),
    ])
    db.session.commit()

    print("Done! Log in with admin@kilimorada.app / password123")
