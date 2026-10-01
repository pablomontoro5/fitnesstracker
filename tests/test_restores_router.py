import sqlite3

from fastapi.testclient import TestClient

from app.db import DATABASE_PATH, get_connection
from app.dependencies import ADMIN_EMAILS_ENV
from app.main import app
from tests.conftest import register_and_login


def admin_headers(client, monkeypatch) -> dict[str, str]:
    monkeypatch.setenv(ADMIN_EMAILS_ENV, "admin@example.com")

    return register_and_login(client, email="admin@example.com")


def build_attacker_database_bytes(tmp_path) -> bytes:
    """Copia válida de la base, pero sin ningún dato de usuarios."""
    attacker_path = tmp_path / "attacker.db"

    with sqlite3.connect(DATABASE_PATH) as source:
        with sqlite3.connect(attacker_path) as destination:
            source.backup(destination)

    with sqlite3.connect(attacker_path) as connection:
        connection.execute("DELETE FROM daily_logs")
        connection.execute("DELETE FROM users")

    return attacker_path.read_bytes()


def count_users() -> int:
    with get_connection() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

def create_test_user_id(connection) -> int:
    cursor = connection.execute(
        """
        INSERT INTO users (
            email,
            display_name,
            password_hash
        )
        VALUES (?, ?, ?)
        """,
        (
            "owner@example.com",
            "Owner",
            "test-password-hash",
        ),
    )

    return cursor.lastrowid

def create_database_backup_bytes() -> bytes:
    with sqlite3.connect(DATABASE_PATH) as connection:
        user_id = create_test_user_id(connection)

        connection.execute(
            """
            INSERT INTO daily_logs (
                user_id,
                date,
                steps,
                notes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                "2026-09-08",
                8500,
                "Base para restaurar.",
            ),
        )

    return DATABASE_PATH.read_bytes()
def test_restore_database_returns_safety_backup_filename(
    tmp_path,
    monkeypatch,
):
    from app.services import backups

    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)

    with TestClient(app) as client:
        headers = admin_headers(client, monkeypatch)
        database_bytes = create_database_backup_bytes()

        response = client.post(
            "/restores/database",
            headers=headers,
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


def test_restore_database_rejects_file_without_db_extension(monkeypatch):
    with TestClient(app) as client:
        headers = admin_headers(client, monkeypatch)
        response = client.post(
            "/restores/database",
            headers=headers,
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


def test_restore_database_rejects_invalid_sqlite_content(monkeypatch):
    with TestClient(app) as client:
        headers = admin_headers(client, monkeypatch)
        response = client.post(
            "/restores/database",
            headers=headers,
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


def test_restore_requires_authentication_and_leaves_data_untouched(
    tmp_path,
    monkeypatch,
):
    from app.services import backups

    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)
    monkeypatch.setenv(ADMIN_EMAILS_ENV, "admin@example.com")

    with TestClient(app) as client:
        register_and_login(client, email="victim@example.com")
        attacker_bytes = build_attacker_database_bytes(tmp_path)

        assert count_users() == 1

        response = client.post(
            "/restores/database",
            files={
                "file": (
                    "attacker.db",
                    attacker_bytes,
                    "application/octet-stream",
                )
            },
        )

        # La autenticación se evalúa antes que la validación del cuerpo.
        missing_file_response = client.post("/restores/database")

    assert response.status_code == 401
    assert missing_file_response.status_code == 401
    assert count_users() == 1
    assert list(tmp_path.glob("fitness_tracker_backup_*.db")) == []


def test_restore_is_forbidden_for_regular_users_and_leaves_data_untouched(
    tmp_path,
    monkeypatch,
):
    from app.services import backups

    monkeypatch.setattr(backups, "BACKUPS_DIR", tmp_path)
    monkeypatch.setenv(ADMIN_EMAILS_ENV, "admin@example.com")

    with TestClient(app) as client:
        headers = register_and_login(client, email="user@example.com")
        attacker_bytes = build_attacker_database_bytes(tmp_path)

        response = client.post(
            "/restores/database",
            headers=headers,
            files={
                "file": (
                    "attacker.db",
                    attacker_bytes,
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 403
    assert count_users() == 1
    assert list(tmp_path.glob("fitness_tracker_backup_*.db")) == []
