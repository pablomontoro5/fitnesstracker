from fastapi.testclient import TestClient

from app.dependencies import ADMIN_EMAILS_ENV
from app.main import app
from app.services import backups
from tests.conftest import register_and_login


def test_backup_requires_authentication(tmp_path, monkeypatch):
    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)

    with TestClient(app) as client:
        response = client.post("/backups/database")

    assert response.status_code == 401
    assert list(tmp_path.iterdir()) == []


def test_backup_is_forbidden_for_regular_users(tmp_path, monkeypatch):
    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)
    monkeypatch.setenv(ADMIN_EMAILS_ENV, "admin@example.com")

    with TestClient(app) as client:
        headers = register_and_login(client, email="user@example.com")
        response = client.post("/backups/database", headers=headers)

    assert response.status_code == 403
    assert list(tmp_path.iterdir()) == []


def test_backup_is_forbidden_when_no_admin_is_configured(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)
    monkeypatch.delenv(ADMIN_EMAILS_ENV, raising=False)

    with TestClient(app) as client:
        headers = register_and_login(client, email="admin@example.com")
        response = client.post("/backups/database", headers=headers)

    assert response.status_code == 403


def test_download_database_backup_returns_sqlite_file_for_admin(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)
    monkeypatch.setenv(ADMIN_EMAILS_ENV, "Admin@Example.com, other@example.com")

    with TestClient(app) as client:
        headers = register_and_login(client, email="admin@example.com")
        response = client.post("/backups/database", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/octet-stream"
    )

    content_disposition = response.headers["content-disposition"]

    assert "attachment" in content_disposition
    assert "fitness_tracker_backup_" in content_disposition
    assert content_disposition.endswith(".db\"")
    assert len(response.content) > 0

    created_backups = list(
        tmp_path.glob("fitness_tracker_backup_*.db")
    )

    assert len(created_backups) == 1
    assert created_backups[0].read_bytes() == response.content
