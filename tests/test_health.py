from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint(monkeypatch, tmp_path) -> None:
    from app import main

    main.database.path = tmp_path / "health.db"

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Document & Proposal Assistant",
        "version": "0.1.0",
        "environment": "development",
        "database": "ok",
    }


def test_health_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    from app import main

    monkeypatch.setattr(main.database, "healthcheck", lambda: False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database health check failed"}

