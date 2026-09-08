import sqlite3

from fastapi.testclient import TestClient

from app.db import DATABASE_PATH
from app.main import app


def create_database_backup_bytes() -> bytes:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO daily_logs (date, steps, notes)
            VALUES (?, ?, ?)
            """,
            ("2026-09-08", 8500, "Base para restaurar."),
        )

    return DATABASE_PATH.read_bytes()


def test_restore_database_returns_safety_backup_filename(
    tmp_path,
    monkeypatch,
):
    from app.services import backups

    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)

    database_bytes = create_database_backup_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/restores/database",
            files={
                "file": (
                    "fitness_tracker_backup.db",
                    database_bytes,
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Base de datos restaurada correctamente."
    )
    assert response.json()["safety_backup_filename"].startswith(
        "fitness_tracker_backup_"
    )
    assert response.json()["safety_backup_filename"].endswith(".db")

    created_backups = list(tmp_path.glob("fitness_tracker_backup_*.db"))

    assert len(created_backups) == 1
    assert created_backups[0].stat().st_size > 0


def test_restore_database_rejects_file_without_db_extension():
    with TestClient(app) as client:
        response = client.post(
            "/restores/database",
            files={
                "file": (
                    "backup.txt",
                    b"Este contenido no importa.",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Debes seleccionar un archivo con extensión .db."
    }


def test_restore_database_rejects_invalid_sqlite_content():
    with TestClient(app) as client:
        response = client.post(
            "/restores/database",
            files={
                "file": (
                    "invalid.db",
                    b"Esto no es un archivo SQLite.",
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "El archivo subido no es una base de datos SQLite válida."
    }