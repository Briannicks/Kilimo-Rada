from config import db
from models import InputReport


def test_admin_adds_batch_code(admin_client):
    response = admin_client.post("/api/batch-codes", json={
        "batch_code": "dap 2026 a01", "product": "DAP 50kg", "manufacturer": "Yara",
    })
    assert response.status_code == 201
    assert response.get_json()["batch_code"] == "DAP2026A01"


def test_duplicate_batch_code(admin_client):
    body = {"batch_code": "ABC123", "product": "CAN", "manufacturer": "X"}
    admin_client.post("/api/batch-codes", json=body)
    assert admin_client.post("/api/batch-codes", json=body).status_code == 409


def test_officer_cannot_add_batch_code(officer_client):
    response = officer_client.post("/api/batch-codes", json={
        "batch_code": "ABC123", "product": "CAN", "manufacturer": "X",
    })
    assert response.status_code == 403


def test_mark_batch_code_fake(admin_client):
    product_id = admin_client.post("/api/batch-codes", json={
        "batch_code": "ABC123", "product": "CAN", "manufacturer": "X",
    }).get_json()["id"]
    response = admin_client.patch(f"/api/batch-codes/{product_id}", json={"status": "fake"})
    assert response.get_json()["status"] == "fake"


def test_agrovet_crud(admin_client):
    created = admin_client.post("/api/agrovets", json={
        "name": "tinet agro", "ward": "tinet", "phone": "0722000111", "license_no": "PCPB-1",
    })
    assert created.status_code == 201
    agrovet_id = created.get_json()["id"]
    assert admin_client.patch(f"/api/agrovets/{agrovet_id}", json={"ward": "Lanet"}).get_json()["ward"] == "Lanet"
    assert admin_client.delete(f"/api/agrovets/{agrovet_id}").status_code == 204


def test_agrovet_bad_phone(admin_client):
    response = admin_client.post("/api/agrovets", json={"name": "Shop", "ward": "Tinet", "phone": "123"})
    assert response.status_code == 422


def test_input_reports_hide_phone_numbers(officer_client):
    db.session.add(InputReport(reference="KRTEST1", phone="+254712345678", kind="batch_code", value="BAD1"))
    db.session.commit()
    item = officer_client.get("/api/input-reports").get_json()["items"][0]
    assert item["reported_by"] == "+25471***678"


def test_ussd_stats_flags_codes(officer_client):
    for i in range(3):
        db.session.add(InputReport(reference=f"KRTST{i}", phone=f"+25470000000{i}",
                                   kind="batch_code", value="BAD123"))
    db.session.commit()
    stats = officer_client.get("/api/ussd-stats").get_json()
    assert stats["fake_input_reports"] == 3
    assert stats["most_reported"][0] == {"value": "BAD123", "kind": "batch_code", "reports": 3, "flagged": True}