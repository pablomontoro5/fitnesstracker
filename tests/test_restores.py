import sqlite3
from contextlib import closing
from datetime import datetime
from io import BytesIO

from fastapi import UploadFile

from app.db import DATABASE_PATH, get_connection
from app.services.restores import restore_database

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


def copy_database_like_a_backup(database_path) -> None:
    """Copia la base activa igual que lo hace la app: un único archivo."""
    with closing(sqlite3.connect(DATABASE_PATH)) as source_connection:
        with closing(sqlite3.connect(database_path)) as destination_connection:
            source_connection.backup(destination_connection)
            destination_connection.execute("PRAGMA journal_mode = DELETE")


def create_valid_database(database_path, user_id: int):
    copy_database_like_a_backup(database_path)

    with sqlite3.connect(database_path) as connection:
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
                9000,
                "Datos restaurados.",
            ),
        )
def test_restore_database_replaces_current_database_and_creates_backup(
    tmp_path,
):
    with get_connection() as connection:
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
                "2026-09-07",
                1000,
                "Datos anteriores.",
            ),
        )

    uploaded_database_path = tmp_path / "uploaded.db"
    create_valid_database(uploaded_database_path, user_id)

    upload = UploadFile(
        filename="fitness_tracker_backup.db",
        file=BytesIO(uploaded_database_path.read_bytes()),
    )

    backup_path = restore_database(
        upload=upload,
        backups_dir=tmp_path / "backups",
        now=datetime(2026, 9, 8, 12, 0, 0),
    )

    assert backup_path == (
        tmp_path / "backups" / "fitness_tracker_backup_2026-09-08_12-00-00.db"
    )
    assert backup_path.exists()

    with sqlite3.connect(backup_path) as connection:
        backup_row = connection.execute(
            """
            SELECT date, steps, notes
            FROM daily_logs
            WHERE date = ?
            """,
            ("2026-09-07",),
        ).fetchone()

    assert backup_row == ("2026-09-07", 1000, "Datos anteriores.")

    with sqlite3.connect(DATABASE_PATH) as connection:
        restored_row = connection.execute(
            """
            SELECT date, steps, notes
            FROM daily_logs
            WHERE date = ?
            """,
            ("2026-09-08",),
        ).fetchone()

    assert restored_row == ("2026-09-08", 9000, "Datos restaurados.")

def test_restore_database_rejects_invalid_sqlite_file(tmp_path):
    upload = UploadFile(
        filename="not_a_database.db",
        file=BytesIO(b"Este archivo no es SQLite."),
    )

    try:
        restore_database(
            upload=upload,            backups_dir=tmp_path / "backups",
        )
    except ValueError as error:
        assert str(error) == (
            "El archivo subido no es una base de datos SQLite válida."
        )
    else:
        raise AssertionError("Se esperaba que la restauración fallara.")


def test_restore_database_rejects_database_with_missing_tables(tmp_path):
    incomplete_database_path = tmp_path / "incomplete.db"

    with sqlite3.connect(incomplete_database_path) as connection:
        connection.execute(
            """
            CREATE TABLE daily_logs (
                id INTEGER PRIMARY KEY
            )
            """
        )

    upload = UploadFile(
        filename="incomplete.db",
        file=BytesIO(incomplete_database_path.read_bytes()),
    )

    try:
        restore_database(
            upload=upload,
            backups_dir=tmp_path / "backups",
        )
    except ValueError as error:
        assert "tablas obligatorias" in str(error)
        assert "workout_templates" in str(error)
    else:
        raise AssertionError("Se esperaba que la restauración fallara.")

def test_restore_database_rejects_database_with_missing_columns(
    tmp_path,
):
    incompatible_database_path = tmp_path / "incompatible.db"

    copy_database_like_a_backup(incompatible_database_path)

    with sqlite3.connect(incompatible_database_path) as connection:
        connection.execute(
            """
            DROP TABLE workout_templates
            """
        )
        connection.execute(
            """
            CREATE TABLE workout_templates (
                id INTEGER PRIMARY KEY
            )
            """
        )

    upload = UploadFile(
        filename="incompatible.db",
        file=BytesIO(incompatible_database_path.read_bytes()),
    )

    try:
        restore_database(
            upload=upload,
            backups_dir=tmp_path / "backups",
        )
    except ValueError as error:
        assert str(error).startswith(
            "El archivo subido no tiene un esquema compatible."
        )
        assert "workout_templates" in str(error)
        assert "name" in str(error)
    else:
        raise AssertionError("Se esperaba que la restauración fallara.")

    assert not (tmp_path / "backups").exists()


def test_restore_accepts_a_database_file_in_wal_mode(tmp_path):
    wal_path = tmp_path / "wal.db"

    with closing(sqlite3.connect(DATABASE_PATH)) as source_connection:
        with closing(sqlite3.connect(wal_path)) as destination_connection:
            source_connection.backup(destination_connection)
            destination_connection.execute("PRAGMA journal_mode = WAL")
            destination_connection.commit()

    # Cabecera con modo WAL (2): la deserialización directa fallaba.
    assert wal_path.read_bytes()[18] == 2

    upload = UploadFile(
        filename="wal.db",
        file=BytesIO(wal_path.read_bytes()),
    )

    backup_path = restore_database(
        upload=upload,
        backups_dir=tmp_path / "backups",
        now=datetime(2026, 9, 8, 12, 0, 0),
    )

    assert backup_path.exists()
