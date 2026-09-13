import sqlite3
from datetime import datetime

from app.db import get_connection
from app.services.backups import create_database_backup
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

def test_create_database_backup_copies_database(tmp_path):
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
                "2026-09-06",
                12345,
                "Registro de prueba.",
            ),
        )

    backup_path = create_database_backup(
        backups_dir=tmp_path,
        now=datetime(2026, 9, 6, 23, 44, 0),
    )

    assert backup_path == (
        tmp_path / "fitness_tracker_backup_2026-09-06_23-44-00.db"
    )
    assert backup_path.exists()
    assert backup_path.stat().st_size > 0

    with sqlite3.connect(backup_path) as connection:
        row = connection.execute(
            """
            SELECT date, steps, notes
            FROM daily_logs
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    assert row == ("2026-09-06", 12345, "Registro de prueba.")