import sqlite3
from datetime import datetime
from io import BytesIO

from fastapi import UploadFile

from app.db import DATABASE_PATH, get_connection
from app.services.restores import restore_database


def create_valid_database(database_path):
    with sqlite3.connect(DATABASE_PATH) as source_connection:
        with sqlite3.connect(database_path) as destination_connection:
            source_connection.backup(destination_connection)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO daily_logs (date, steps, notes)
            VALUES (?, ?, ?)
            """,
            ("2026-09-08", 9000, "Datos restaurados."),
        )

def test_restore_database_replaces_current_database_and_creates_backup(
    tmp_path,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO daily_logs (date, steps, notes)
            VALUES (?, ?, ?)
            """,
            ("2026-09-07", 1000, "Datos anteriores."),
        )

    uploaded_database_path = tmp_path / "uploaded.db"
    create_valid_database(uploaded_database_path)

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

    with sqlite3.connect(incompatible_database_path) as connection:
        with sqlite3.connect(DATABASE_PATH) as source_connection:
            source_connection.backup(connection)

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