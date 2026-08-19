import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "fitness_tracker.db"


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión configurada con la base de datos SQLite."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")

    return connection


def initialize_database() -> None:
    """Crea las tablas necesarias si todavía no existen."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                steps INTEGER NOT NULL DEFAULT 0 CHECK (steps >= 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS body_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                weight_kg REAL NOT NULL CHECK (weight_kg > 0),
                height_cm REAL NOT NULL CHECK (height_cm > 0),
                bmi REAL NOT NULL CHECK (bmi > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_session_id INTEGER NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                muscle_group TEXT NOT NULL CHECK (length(trim(muscle_group)) > 0),
                position INTEGER NOT NULL CHECK (position > 0),
                technique_notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workout_session_id)
                    REFERENCES workout_sessions(id)
                    ON DELETE CASCADE,
                UNIQUE (workout_session_id, position)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_exercise_id INTEGER NOT NULL,
                set_type TEXT NOT NULL CHECK (
                    set_type IN ('warmup', 'approximation', 'working', 'drop_set')
                ),
                position INTEGER NOT NULL CHECK (position > 0),
                target_rep_range TEXT,
                repetitions INTEGER NOT NULL CHECK (repetitions > 0),
                weight_kg REAL NOT NULL CHECK (weight_kg >= 0),
                rir REAL CHECK (rir >= -3 AND rir <= 10),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workout_exercise_id)
                    REFERENCES workout_exercises(id)
                    ON DELETE CASCADE,
                UNIQUE (workout_exercise_id, position)
            )
            """
        )