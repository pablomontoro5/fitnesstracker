import sqlite3
from datetime import datetime
from pathlib import Path

from app.db import DATA_DIR, DATABASE_PATH


BACKUPS_DIR = DATA_DIR / "backups"


def create_database_backup(
    backups_dir: Path = BACKUPS_DIR,
    now: datetime | None = None,
) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backups_dir / f"fitness_tracker_backup_{timestamp}.db"

    with sqlite3.connect(DATABASE_PATH) as source_connection:
        with sqlite3.connect(backup_path) as destination_connection:
            source_connection.backup(destination_connection)

    return backup_path