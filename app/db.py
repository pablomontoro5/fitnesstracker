import os
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

DATABASE_FILENAME = (
    "fitness_tracker_test.db"
    if os.environ.get("FITNESS_TRACKER_TESTING") == "1"
    else "fitness_tracker.db"
)

DATABASE_PATH = DATA_DIR / DATABASE_FILENAME

FITNESS_GOAL_TYPES = (
    "daily_steps",
    "weekly_workouts",
    "weekly_running_km",
    "daily_calories",
    "daily_protein_g",
    "daily_carbs_g",
    "daily_fat_g",
    "daily_sleep_minutes",
    "weekly_rest_days",
)

FITNESS_GOAL_TYPES_SQL = ", ".join(
    f"'{goal_type}'"
    for goal_type in FITNESS_GOAL_TYPES
)

def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión configurada con la base de datos SQLite."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")

    return connection

def migrate_fitness_goals_table(
    connection: sqlite3.Connection,
) -> None:
    table_sql_row = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
            AND name = 'fitness_goals'
        """
    ).fetchone()

    if table_sql_row is None:
        return

    table_sql = table_sql_row["sql"] or ""

    if all(goal_type in table_sql for goal_type in FITNESS_GOAL_TYPES):
        return

    connection.execute(
        f"""
        CREATE TABLE fitness_goals_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_type TEXT NOT NULL UNIQUE CHECK (
                goal_type IN ({FITNESS_GOAL_TYPES_SQL})
            ),
            target_value REAL NOT NULL CHECK (target_value > 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        INSERT INTO fitness_goals_new (
            id,
            goal_type,
            target_value,
            created_at,
            updated_at
        )
        SELECT
            id,
            goal_type,
            target_value,
            created_at,
            updated_at
        FROM fitness_goals
        """
    )

    connection.execute("DROP TABLE fitness_goals")
    connection.execute(
        "ALTER TABLE fitness_goals_new RENAME TO fitness_goals"
    )
def initialize_database() -> None:

    """Crea las tablas necesarias si todavía no existen."""
    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE
                    CHECK (length(trim(email)) BETWEEN 3 AND 254),
                display_name TEXT NOT NULL
                    CHECK (length(trim(display_name)) BETWEEN 1 AND 80),
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
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
            CREATE TABLE IF NOT EXISTS daily_recovery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                sleep_minutes INTEGER
                    CHECK (sleep_minutes >= 0 AND sleep_minutes <= 1440),
                sleep_quality INTEGER
                    CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
                is_rest_day INTEGER NOT NULL DEFAULT 0
                    CHECK (is_rest_day IN (0, 1)),
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
                body_fat_percentage REAL
                    CHECK (body_fat_percentage > 0 AND body_fat_percentage < 100),
                waist_cm REAL CHECK (waist_cm > 0 AND waist_cm <= 300),
                hip_cm REAL CHECK (hip_cm > 0 AND hip_cm <= 300),
                chest_cm REAL CHECK (chest_cm > 0 AND chest_cm <= 300),
                arm_cm REAL CHECK (arm_cm > 0 AND arm_cm <= 200),
                thigh_cm REAL CHECK (thigh_cm > 0 AND thigh_cm <= 300),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        body_metric_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(body_metrics)"
            ).fetchall()
        }

        body_metric_composition_columns = {
            "body_fat_percentage": (
                "REAL CHECK (body_fat_percentage > 0 AND body_fat_percentage < 100)"
            ),
            "waist_cm": "REAL CHECK (waist_cm > 0 AND waist_cm <= 300)",
            "hip_cm": "REAL CHECK (hip_cm > 0 AND hip_cm <= 300)",
            "chest_cm": "REAL CHECK (chest_cm > 0 AND chest_cm <= 300)",
            "arm_cm": "REAL CHECK (arm_cm > 0 AND arm_cm <= 200)",
            "thigh_cm": "REAL CHECK (thigh_cm > 0 AND thigh_cm <= 300)",
        }

        for column_name, column_definition in body_metric_composition_columns.items():
            if column_name not in body_metric_columns:
                connection.execute(
                    f"ALTER TABLE body_metrics "
                    f"ADD COLUMN {column_name} {column_definition}"
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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                distance_km REAL NOT NULL CHECK (distance_km > 0),
                duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
                average_pace_seconds_km REAL NOT NULL
                    CHECK (average_pace_seconds_km > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS nutrition_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS nutrition_meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nutrition_day_id INTEGER NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                position INTEGER NOT NULL CHECK (position > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (nutrition_day_id)
                    REFERENCES nutrition_days(id)
                    ON DELETE CASCADE,
                UNIQUE (nutrition_day_id, position)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS nutrition_foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nutrition_meal_id INTEGER NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                quantity_g REAL NOT NULL CHECK (quantity_g > 0),
                calories REAL NOT NULL CHECK (calories >= 0),
                protein_g REAL NOT NULL CHECK (protein_g >= 0),
                carbs_g REAL NOT NULL CHECK (carbs_g >= 0),
                fat_g REAL NOT NULL CHECK (fat_g >= 0),
                position INTEGER NOT NULL CHECK (position > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (nutrition_meal_id)
                    REFERENCES nutrition_meals(id)
                    ON DELETE CASCADE,
                UNIQUE (nutrition_meal_id, position)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_template_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_template_id INTEGER NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                muscle_group TEXT NOT NULL CHECK (length(trim(muscle_group)) > 0),
                position INTEGER NOT NULL CHECK (position > 0),
                technique_notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workout_template_id)
                    REFERENCES workout_templates(id)
                    ON DELETE CASCADE,
                UNIQUE (workout_template_id, position)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_template_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_template_exercise_id INTEGER NOT NULL,
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
                FOREIGN KEY (workout_template_exercise_id)
                    REFERENCES workout_template_exercises(id)
                    ON DELETE CASCADE,
                UNIQUE (workout_template_exercise_id, position)
            )
            """
        )

        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS fitness_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL UNIQUE CHECK (
                    goal_type IN ({FITNESS_GOAL_TYPES_SQL})
                ),
                target_value REAL NOT NULL CHECK (target_value > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        migrate_fitness_goals_table(connection)
