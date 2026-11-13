from config import db
from models import Farmer


def add_farmers():
    db.session.add_all([
        Farmer(name="Maize One", phone="0712000001", main_crop="Maize", registered_via="web"),
        Farmer(name="Maize Two", phone="0712000002", main_crop="Maize", registered_via="ussd"),
        Farmer(name="Bean One", phone="0712000003", main_crop="Beans", registered_via="web"),
    ])
    db.session.commit()


def test_broadcast_to_all(officer_client, sms_outbox):
    add_farmers()
    response = officer_client.post("/api/broadcasts", json={"message": "Heavy rain expected."})
    assert response.status_code == 201
    assert response.get_json()["recipient_count"] == 3
    assert len(sms_outbox[0]["to"]) == 3


def test_broadcast_to_one_crop(officer_client, sms_outbox):
    add_farmers()
    response = officer_client.post("/api/broadcasts", json={"message": "Armyworm alert", "target_crop": "maize"})
    assert response.get_json()["recipient_count"] == 2
    assert response.get_json()["target_crop"] == "Maize"


def test_message_too_long(officer_client, sms_outbox):
    add_farmers()
    response = officer_client.post("/api/broadcasts", json={"message": "x" * 161})
    assert response.status_code == 422
    assert sms_outbox == []  # nothing sent


def test_no_matching_farmers(officer_client, sms_outbox):
    add_farmers()
    response = officer_client.post("/api/broadcasts", json={"message": "Hi", "target_crop": "Rice"})
    assert response.status_code == 400


def test_history(officer_client, sms_outbox):
    add_farmers()
    officer_client.post("/api/broadcasts", json={"message": "First"})
    officer_client.post("/api/broadcasts", json={"message": "Second"})
    data = officer_client.get("/api/broadcasts").get_json()
    assert data["total"] == 2
    assert data["items"][0]["sender"] == "Field Officer"