from fastapi.testclient import TestClient

from app.main import app


def test_download_database_backup_returns_sqlite_file():
    with TestClient(app) as client:
        response = client.post("/backups/database")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"

    content_disposition = response.headers["content-disposition"]

    assert "attachment" in content_disposition
    assert "fitness_tracker_backup_" in content_disposition
    assert content_disposition.endswith(".db\"")
    assert len(response.content) > 0