import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from app.db import DATABASE_PATH
from app.services.backups import create_database_backup


REQUIRED_TABLES = {
    "daily_logs",
    "body_metrics",
    "workout_sessions",
    "workout_exercises",
    "workout_sets",
    "runs",
    "nutrition_days",
    "nutrition_meals",
    "nutrition_foods",
    "workout_templates",
    "workout_template_exercises",
    "workout_template_sets",
}
REQUIRED_COLUMNS = {
    "daily_logs": {
        "id",
        "date",
        "steps",
        "notes",
        "created_at",
    },
    "body_metrics": {
        "id",
        "date",
        "weight_kg",
        "height_cm",
        "bmi",
        "notes",
        "created_at",
    },
    "workout_sessions": {
        "id",
        "date",
        "name",
        "notes",
        "created_at",
    },
    "workout_exercises": {
        "id",
        "workout_session_id",
        "name",
        "muscle_group",
        "position",
        "technique_notes",
        "created_at",
    },
    "workout_sets": {
        "id",
        "workout_exercise_id",
        "set_type",
        "position",
        "target_rep_range",
        "repetitions",
        "weight_kg",
        "rir",
        "notes",
        "created_at",
    },
    "runs": {
        "id",
        "date",
        "distance_km",
        "duration_seconds",
        "average_pace_seconds_km",
        "notes",
        "created_at",
    },
    "nutrition_days": {
        "id",
        "date",
        "notes",
        "created_at",
    },
    "nutrition_meals": {
        "id",
        "nutrition_day_id",
        "name",
        "position",
        "created_at",
    },
    "nutrition_foods": {
        "id",
        "nutrition_meal_id",
        "name",
        "quantity_g",
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "position",
        "notes",
        "created_at",
    },
    "workout_templates": {
        "id",
        "name",
        "notes",
        "created_at",
    },
    "workout_template_exercises": {
        "id",
        "workout_template_id",
        "name",
        "muscle_group",
        "position",
        "technique_notes",
        "created_at",
    },
    "workout_template_sets": {
        "id",
        "workout_template_exercise_id",
        "set_type",
        "position",
        "target_rep_range",
        "repetitions",
        "weight_kg",
        "rir",
        "notes",
        "created_at",
    },
}

def _get_database_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    return {row[0] for row in rows}

def _get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM pragma_table_info(?)
        """,
        (table_name,),
    ).fetchall()

    return {row[0] for row in rows}

def _validate_database_integrity(connection: sqlite3.Connection) -> None:
    try:
        result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
    except sqlite3.DatabaseError as error:
        raise ValueError(
            "El archivo subido no es una base de datos SQLite válida."
        ) from error

    if result != "ok":
        raise ValueError(
            "El archivo subido contiene una base de datos SQLite dañada."
        )


def _validate_required_tables(connection: sqlite3.Connection) -> None:
    database_tables = _get_database_tables(connection)
    missing_tables = sorted(REQUIRED_TABLES - database_tables)

    if missing_tables:
        missing_tables_text = ", ".join(missing_tables)
        raise ValueError(
            "El archivo subido no contiene las tablas obligatorias: "
            f"{missing_tables_text}."
        )

def _validate_required_columns(
    connection: sqlite3.Connection,
) -> None:
    missing_columns_by_table: list[str] = []

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        actual_columns = _get_table_columns(
            connection=connection,
            table_name=table_name,
        )
        missing_columns = sorted(required_columns - actual_columns)

        if missing_columns:
            missing_columns_text = ", ".join(missing_columns)
            missing_columns_by_table.append(
                f"{table_name} ({missing_columns_text})"
            )

    if missing_columns_by_table:
        details = "; ".join(missing_columns_by_table)
        raise ValueError(
            "El archivo subido no tiene un esquema compatible. "
            f"Faltan columnas obligatorias: {details}."
        )

    
def _get_uploaded_database_connection(
    upload: UploadFile,
) -> sqlite3.Connection:
    uploaded_database = sqlite3.connect(":memory:")

    try:
        uploaded_database.deserialize(upload.file.read())
        return uploaded_database
    except sqlite3.DatabaseError as error:
        uploaded_database.close()
        raise ValueError(
            "El archivo subido no es una base de datos SQLite válida."
        ) from error


def restore_database(
    upload: UploadFile,
    backups_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    uploaded_database = _get_uploaded_database_connection(upload)

    try:
        _validate_database_integrity(uploaded_database)
        _validate_required_tables(uploaded_database)
        _validate_required_columns(uploaded_database)

        backup_path = create_database_backup(
            backups_dir=backups_dir,
            now=now,
        )

        with sqlite3.connect(DATABASE_PATH) as current_database:
            uploaded_database.backup(current_database)

        return backup_path
    finally:
        uploaded_database.close()

