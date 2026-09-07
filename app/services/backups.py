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

    with sqlite3.connect(DATABASE_PATH) as source_connection:
        with sqlite3.connect(backup_path) as destination_connection:
            source_connection.backup(destination_connection)

    return backup_path