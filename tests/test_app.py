def test_health_returns_json(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
