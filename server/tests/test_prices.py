PRICE = {"crop": "maize", "market": "nakuru", "unit": "90kg bag", "price": 3800}


def test_create_price(officer_client):
    response = officer_client.post("/api/prices", json=PRICE)
    assert response.status_code == 201
    data = response.get_json()
    assert data["crop"] == "Maize"
    assert data["posted_by"] == "Field Officer"


def test_invalid_prices(officer_client):
    assert officer_client.post("/api/prices", json={**PRICE, "price": 0}).status_code == 422
    assert officer_client.post("/api/prices", json={**PRICE, "price": "abc"}).status_code == 422
    assert officer_client.post("/api/prices", json={**PRICE, "unit": ""}).status_code == 422


def test_filter_by_crop(officer_client):
    officer_client.post("/api/prices", json=PRICE)
    officer_client.post("/api/prices", json={**PRICE, "crop": "Beans"})
    assert officer_client.get("/api/prices?crop=maize").get_json()["total"] == 1


def test_owner_can_edit(officer_client):
    price_id = officer_client.post("/api/prices", json=PRICE).get_json()["id"]
    response = officer_client.patch(f"/api/prices/{price_id}", json={"price": 4000})
    assert response.get_json()["price"] == 4000


def test_other_officer_cannot_edit_or_delete(officer_client, make_user, login_as):
    price_id = officer_client.post("/api/prices", json=PRICE).get_json()["id"]
    make_user("other@test.com", role="officer")
    other = login_as("other@test.com")
    assert other.patch(f"/api/prices/{price_id}", json={"price": 1}).status_code == 403
    assert other.delete(f"/api/prices/{price_id}").status_code == 403


def test_admin_can_edit_anyones_price(officer_client, admin_client):
    price_id = officer_client.post("/api/prices", json=PRICE).get_json()["id"]
    assert admin_client.patch(f"/api/prices/{price_id}", json={"price": 3900}).status_code == 200
    assert admin_client.delete(f"/api/prices/{price_id}").status_code == 204