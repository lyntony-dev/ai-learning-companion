from fastapi.testclient import TestClient

from app.main import app


def test_version_returns_service_metadata() -> None:
    client = TestClient(app)

    response = client.get("/api/version")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ai-agent-course-tutor-api"
    assert body["version"] == "0.2.0"
    assert body["environment"] == "local"
