from fastapi.testclient import TestClient

from app.main import app
from app.services import backups


def test_download_database_backup_returns_sqlite_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)

    with TestClient(app) as client:
        response = client.post("/backups/database")

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