from models import User


def test_signup_first_user_becomes_admin(client):
    response = client.post("/api/signup", json={
        "name": "Jane Wanjiru", "email": "Jane@Example.com", "password": "password123",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["role"] == "admin"
    assert data["email"] == "jane@example.com"
    assert "password_hash" not in data


def test_second_signup_is_officer(client, admin):
    response = client.post("/api/signup", json={
        "name": "Second User", "email": "second@example.com", "password": "password123",
    })
    assert response.get_json()["role"] == "officer"


def test_signup_duplicate_email(client, admin):
    response = client.post("/api/signup", json={
        "name": "Copy", "email": "admin@test.com", "password": "password123",
    })
    assert response.status_code == 409


def test_signup_short_password(client):
    response = client.post("/api/signup", json={
        "name": "Jane", "email": "jane@example.com", "password": "short",
    })
    assert response.status_code == 422


def test_password_is_hashed(app, admin):
    assert admin.password_hash != "password123"
    assert admin.authenticate("password123")
    assert not admin.authenticate("wrong")


def test_login_wrong_password(client, admin):
    response = client.post("/api/login", json={"email": "admin@test.com", "password": "wrong"})
    assert response.status_code == 401


def test_me_and_logout(admin_client):
    assert admin_client.get("/api/me").get_json()["email"] == "admin@test.com"
    assert admin_client.delete("/api/logout").status_code == 204
    assert admin_client.get("/api/me").status_code == 401


def test_two_step_login(app, client, admin, email_outbox):
    app.config["TWO_FACTOR_ENABLED"] = True

    step1 = client.post("/api/login", json={"email": "admin@test.com", "password": "password123"})
    assert step1.get_json()["two_factor_required"] is True
    assert client.get("/api/me").status_code == 401  # not logged in yet

    assert client.post("/api/verify-otp", json={"code": "000000"}).status_code == 401
    step2 = client.post("/api/verify-otp", json={"code": email_outbox[-1]})
    assert step2.status_code == 200
    assert client.get("/api/me").status_code == 200


def test_otp_can_only_be_used_once(app, admin):
    code = admin.generate_otp()
    assert admin.verify_otp(code) is True
    assert admin.verify_otp(code) is False


def test_too_many_wrong_codes(app, client, admin, email_outbox):
    app.config["TWO_FACTOR_ENABLED"] = True
    client.post("/api/login", json={"email": "admin@test.com", "password": "password123"})
    for _ in range(5):
        client.post("/api/verify-otp", json={"code": "000000"})
    response = client.post("/api/verify-otp", json={"code": email_outbox[-1]})
    assert response.status_code == 429


def test_resend_code(app, client, admin, email_outbox):
    app.config["TWO_FACTOR_ENABLED"] = True
    client.post("/api/login", json={"email": "admin@test.com", "password": "password123"})
    assert client.post("/api/resend-otp").status_code == 200
    assert len(email_outbox) == 2
    # the first code no longer works
    assert client.post("/api/verify-otp", json={"code": email_outbox[0]}).status_code == 401


def test_user_email_is_validated(app):
    try:
        User(name="Bad", email="not-an-email", role="officer")
        assert False, "should have raised"
    except ValueError:
        pass