from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_check():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert isinstance(data["demo_mode"], bool)
    assert data["sources"]["imerg"] == (
        "cached" if data["demo_mode"] else "ok"
    )

def test_crops_catalog_endpoint():
    res = client.get("/api/v1/crops")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_reference_seasons():
    res = client.get("/api/v1/reference/seasons")
    assert res.status_code == 200
    data = res.json()
    assert "seasons" in data
    assert len(data["seasons"]) >= 3
