def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found"}


def test_wrong_method_returns_json_405(client):
    response = client.put("/api/health")
    assert response.status_code == 405
    assert "error" in response.get_json()


def test_swagger_docs_load(client):
    assert client.get("/apidocs/").status_code == 200
    assert client.get("/apispec_1.json").status_code == 200


def test_protected_routes_need_login(client):
    for url in ("/api/farmers", "/api/reports", "/api/prices", "/api/broadcasts", "/api/dashboard"):
        assert client.get(url).status_code == 401, url