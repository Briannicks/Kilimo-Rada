def make_report(test_client, farmer, category="pest", description="Armyworm on maize"):
    response = test_client.post("/api/reports", json={
        "farmer_id": farmer.id, "category": category, "description": description,
    })
    assert response.status_code == 201
    return response.get_json()


def test_create_report(officer_client, farmer):
    report = make_report(officer_client, farmer)
    assert report["status"] == "open"
    assert report["farmer"]["name"] == "John Kiprop"


def test_report_for_missing_farmer(officer_client):
    response = officer_client.post("/api/reports", json={"farmer_id": 999, "description": "Help"})
    assert response.status_code == 404


def test_invalid_category(officer_client, farmer):
    response = officer_client.post("/api/reports", json={
        "farmer_id": farmer.id, "category": "aliens", "description": "Strange lights",
    })
    assert response.status_code == 422


def test_filters(officer_client, farmer):
    make_report(officer_client, farmer, "pest")
    make_report(officer_client, farmer, "disease", "Yellow leaves")
    assert officer_client.get("/api/reports?category=pest").get_json()["total"] == 1
    assert officer_client.get("/api/reports?status=open").get_json()["total"] == 2
    assert officer_client.get("/api/reports?ward=tinet").get_json()["total"] == 2
    assert officer_client.get("/api/reports?ward=molo").get_json()["total"] == 0


def test_reply_sends_sms_and_resolves(officer_client, farmer, sms_outbox):
    report = make_report(officer_client, farmer)
    response = officer_client.post(f"/api/reports/{report['id']}/reply",
                                   json={"message": "Spray with neem today."})
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "resolved"
    assert data["replied_by"] == "Field Officer"
    assert sms_outbox[0]["to"] == ["+254712000001"]
    assert "Spray with neem" in sms_outbox[0]["message"]


def test_empty_reply_rejected(officer_client, farmer, sms_outbox):
    report = make_report(officer_client, farmer)
    response = officer_client.post(f"/api/reports/{report['id']}/reply", json={"message": "  "})
    assert response.status_code == 422
    assert sms_outbox == []


def test_update_status(officer_client, farmer):
    report = make_report(officer_client, farmer)
    response = officer_client.patch(f"/api/reports/{report['id']}", json={"status": "resolved"})
    assert response.get_json()["status"] == "resolved"


def test_only_admin_deletes(officer_client, admin_client, farmer):
    report = make_report(officer_client, farmer)
    assert officer_client.delete(f"/api/reports/{report['id']}").status_code == 403
    assert admin_client.delete(f"/api/reports/{report['id']}").status_code == 204