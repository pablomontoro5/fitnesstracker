import sqlite3
from datetime import datetime
from pathlib import Path

from app.db import DATA_DIR, DATABASE_PATH


BACKUPS_DIR = DATA_DIR / "backups"


def create_database_backup(
    backups_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    backup_directory = backups_dir or BACKUPS_DIR
    backup_directory.mkdir(parents=True, exist_ok=True)

    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_directory / f"fitness_tracker_backup_{timestamp}.db"

    source_connection = sqlite3.connect(DATABASE_PATH)
    destination_connection = sqlite3.connect(backup_path)

    try:
        source_connection.backup(destination_connection)
        # .backup() hereda el modo WAL de la base activa. La copia debe ser
        # un único archivo portable y restaurable.
        destination_connection.execute("PRAGMA journal_mode = DELETE")
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()

    return backup_path