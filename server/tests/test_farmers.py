from models import Farmer


def test_create_farmer_cleans_phone(officer_client):
    response = officer_client.post("/api/farmers", json={
        "name": "Mary Chebet", "phone": "0722 111 222", "ward": "tinet", "main_crop": "beans",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["phone"] == "+254722111222"
    assert data["ward"] == "Tinet"
    assert data["registered_via"] == "web"


def test_duplicate_phone_rejected(officer_client, farmer):
    response = officer_client.post("/api/farmers", json={"name": "Copy", "phone": "+254712000001"})
    assert response.status_code == 409


def test_invalid_phone_rejected(officer_client):
    response = officer_client.post("/api/farmers", json={"name": "Bad Phone", "phone": "12345"})
    assert response.status_code == 422


def test_phone_formats():
    assert Farmer.normalize_phone("0712345678") == "+254712345678"
    assert Farmer.normalize_phone("254712345678") == "+254712345678"
    assert Farmer.normalize_phone("+254 712 345 678") == "+254712345678"


def test_search_and_filters(officer_client, farmer):
    officer_client.post("/api/farmers", json={
        "name": "Peter Mwangi", "phone": "0712000003", "ward": "Lanet", "main_crop": "Potatoes",
    })
    assert officer_client.get("/api/farmers?search=kiprop").get_json()["total"] == 1
    assert officer_client.get("/api/farmers?search=712000003").get_json()["total"] == 1
    assert officer_client.get("/api/farmers?ward=lanet").get_json()["total"] == 1
    assert officer_client.get("/api/farmers?crop=maize").get_json()["total"] == 1


def test_pagination(officer_client):
    for i in range(12):
        officer_client.post("/api/farmers", json={"name": f"Farmer {i}", "phone": f"07120000{i:02d}"})
    data = officer_client.get("/api/farmers?page=2&per_page=5").get_json()
    assert data["total"] == 12
    assert data["page"] == 2
    assert data["pages"] == 3
    assert len(data["items"]) == 5


def test_get_farmer_includes_reports(officer_client, farmer):
    officer_client.post("/api/reports", json={
        "farmer_id": farmer.id, "category": "pest", "description": "Armyworm",
    })
    data = officer_client.get(f"/api/farmers/{farmer.id}").get_json()
    assert len(data["reports"]) == 1


def test_update_farmer(officer_client, farmer):
    response = officer_client.patch(f"/api/farmers/{farmer.id}", json={"ward": "molo"})
    assert response.get_json()["ward"] == "Molo"


def test_update_to_taken_phone(officer_client, farmer):
    other = officer_client.post("/api/farmers", json={"name": "Other", "phone": "0712000009"})
    response = officer_client.patch(f"/api/farmers/{other.get_json()['id']}", json={"phone": "0712000001"})
    assert response.status_code == 409


def test_officer_cannot_delete(officer_client, farmer):
    assert officer_client.delete(f"/api/farmers/{farmer.id}").status_code == 403


def test_admin_delete_removes_reports(admin_client, farmer):
    admin_client.post("/api/reports", json={"farmer_id": farmer.id, "description": "Help please"})
    assert admin_client.delete(f"/api/farmers/{farmer.id}").status_code == 204
    assert admin_client.get(f"/api/farmers/{farmer.id}").status_code == 404
    assert admin_client.get("/api/reports").get_json()["total"] == 0


def test_missing_farmer_404(officer_client):
    assert officer_client.get("/api/farmers/999").status_code == 404