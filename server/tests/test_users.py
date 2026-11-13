import io


def test_admin_can_list_users(admin_client, officer):
    response = admin_client.get("/api/users")
    assert response.status_code == 200
    assert response.get_json()["total"] == 2


def test_officer_cannot_list_users(officer_client):
    assert officer_client.get("/api/users").status_code == 403


def test_admin_changes_role(admin_client, officer):
    response = admin_client.patch(f"/api/users/{officer.id}/role", json={"role": "admin"})
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"


def test_admin_cannot_change_own_role(admin_client, admin):
    response = admin_client.patch(f"/api/users/{admin.id}/role", json={"role": "officer"})
    assert response.status_code == 400


def test_invalid_role(admin_client, officer):
    response = admin_client.patch(f"/api/users/{officer.id}/role", json={"role": "king"})
    assert response.status_code == 422


def test_update_my_name(officer_client):
    response = officer_client.patch("/api/users/me", json={"name": "New Name"})
    assert response.get_json()["name"] == "New Name"


def test_upload_avatar(officer_client):
    response = officer_client.patch(
        "/api/users/me",
        data={"avatar": (io.BytesIO(b"fake image"), "me.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["avatar_url"]


def test_reject_non_image_avatar(officer_client):
    response = officer_client.patch(
        "/api/users/me",
        data={"avatar": (io.BytesIO(b"virus"), "file.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 422


def test_dashboard_counts(officer_client, farmer):
    officer_client.post("/api/reports", json={
        "farmer_id": farmer.id, "category": "pest", "description": "Armyworm",
    })
    data = officer_client.get("/api/dashboard").get_json()
    assert data["total_farmers"] == 1
    assert data["open_reports"] == 1
    assert data["reports_by_category"]["pest"] == 1
    assert len(data["recent_reports"]) == 1