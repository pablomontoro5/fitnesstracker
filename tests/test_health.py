from fastapi.testclient import TestClient

from app import main
from app.main import app


def test_health_check_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_check_returns_503_when_database_is_down(monkeypatch):
    def broken_check() -> None:
        raise RuntimeError("postgresql://usuario:secreto@host/db")

    with TestClient(app) as client:
        monkeypatch.setattr(main, "check_database", broken_check)
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
    assert "secreto" not in response.text
