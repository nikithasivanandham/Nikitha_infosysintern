from fastapi.testclient import TestClient
from app.main import app
from app import __version__

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "healthy",
        "version": __version__,
    }
