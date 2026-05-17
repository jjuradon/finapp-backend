from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["status"] in ["ok", "degraded", "unavailable"]
