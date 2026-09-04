from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_init_database_endpoint_applies_migrations(tmp_path: Path) -> None:
    db_path = tmp_path / "app.sqlite"

    def override_settings():  # type: ignore[no-untyped-def]
        from app.core.config import Settings

        return Settings(DATABASE_URL=f"sqlite:///{db_path}")

    app.dependency_overrides[get_settings] = override_settings
    try:
        client = TestClient(app)
        response = client.post("/api/admin/db/init")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "applied_migrations": ["001_initial_schema", "002_message_full_fidelity"],
    }
    assert db_path.exists()
