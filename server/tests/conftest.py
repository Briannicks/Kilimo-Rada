
import os
import sys


os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TWO_FACTOR_ENABLED"] = "false"
for key in ("AT_API_KEY", "SENDGRID_API_KEY", "CLOUDINARY_URL", "GEMINI_API_KEY", "GEMINI_MODEL"):
    os.environ[key] = ""

import pytest  

from app import app as flask_app  
from config import db  
from models import Farmer, User  


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["TWO_FACTOR_ENABLED"] = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()



@pytest.fixture
def make_user(app):
    def _make_user(email, role="officer", name="Test User", password="password123"):
        user = User(name=name, email=email, role=role)
        user.password = password
        db.session.add(user)
        db.session.commit()
        return user
    return _make_user


@pytest.fixture
def admin(make_user):
    return make_user("admin@test.com", role="admin", name="Admin User")


@pytest.fixture
def officer(make_user):
    return make_user("officer@test.com", role="officer", name="Field Officer")


def log_in(test_client, email, password="password123"):
    response = test_client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return test_client


@pytest.fixture
def login_as(app):
    """Returns a NEW logged-in client, e.g. login_as("someone@test.com")."""
    return lambda email: log_in(app.test_client(), email)


@pytest.fixture
def admin_client(app, admin):
    return log_in(app.test_client(), admin.email)


@pytest.fixture
def officer_client(app, officer):
    return log_in(app.test_client(), officer.email)



@pytest.fixture
def farmer(app):
    farmer = Farmer(name="John Kiprop", phone="0712000001", ward="Tinet",
                    main_crop="Maize", registered_via="web")
    db.session.add(farmer)
    db.session.commit()
    return farmer



@pytest.fixture
def sms_outbox(monkeypatch):
    """Catches every SMS instead of sending it. Background tasks run immediately."""
    sent = []

    def fake_send_sms(phones, message):
        sent.append({"to": phones, "message": message})
        return {"sent": len(phones), "failed": 0}

    for module in ("routes.reports", "routes.broadcasts", "ussd_helpers"):
        monkeypatch.setattr(sys.modules[module], "send_sms", fake_send_sms)
    for module in ("ussd_helpers", "routes.ussd"):
        monkeypatch.setattr(sys.modules[module], "run_in_background", lambda fn, *args: fn(*args))
    return sent


@pytest.fixture
def email_outbox(monkeypatch):
    """Catches 2FA emails and keeps the codes."""
    codes = []
    monkeypatch.setattr(sys.modules["routes.auth"], "send_otp_email",
                        lambda to, code: codes.append(code) or True)
    return codes