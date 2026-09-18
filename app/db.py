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

BODY_COMPOSITION_GOAL_METRIC_TYPES = (
    "weight_kg",
    "body_fat_percentage",
    "waist_cm",
    "hip_cm",
    "chest_cm",
    "arm_cm",
    "thigh_cm",
)

BODY_COMPOSITION_GOAL_DIRECTIONS = (
    "decrease",
    "increase",
    "maintain",
)

BODY_COMPOSITION_GOAL_METRIC_TYPES_SQL = ", ".join(
    f"'{metric_type}'"
    for metric_type in BODY_COMPOSITION_GOAL_METRIC_TYPES
)

BODY_COMPOSITION_GOAL_DIRECTIONS_SQL = ", ".join(
    f"'{direction}'"
    for direction in BODY_COMPOSITION_GOAL_DIRECTIONS
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
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(fitness_goals)"
        ).fetchall()
    }

    if "user_id" in columns:
        return

    first_user_row = connection.execute(
        """
        SELECT id
        FROM users
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()

    legacy_goals_count = connection.execute(
        "SELECT COUNT(*) AS count FROM fitness_goals"
    ).fetchone()["count"]

    if first_user_row is None and legacy_goals_count > 0:
        raise RuntimeError(
            "No se pueden migrar objetivos sin un usuario propietario."
        )

    if first_user_row is None:
        return

    legacy_user_id = first_user_row["id"]

    connection.execute(
        f"""
        CREATE TABLE fitness_goals_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_type TEXT NOT NULL CHECK (
                goal_type IN ({FITNESS_GOAL_TYPES_SQL})
            ),
            target_value REAL NOT NULL CHECK (target_value > 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            UNIQUE (user_id, goal_type)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO fitness_goals_new (
            id,
            user_id,
            goal_type,
            target_value,
            created_at,
            updated_at
        )
        SELECT
            id,
            ?,
            goal_type,
            target_value,
            created_at,
            updated_at
        FROM fitness_goals
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE fitness_goals")
    connection.execute(
        "ALTER TABLE fitness_goals_new RENAME TO fitness_goals"
    )
def migrate_daily_logs_table(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(daily_logs)"
        ).fetchall()
    }

    if "user_id" in columns:
        return
    first_user_row = connection.execute(
        """
        SELECT id
        FROM users
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()

    legacy_logs_count = connection.execute(
        "SELECT COUNT(*) AS count FROM daily_logs"
    ).fetchone()["count"]

    if first_user_row is None and legacy_logs_count > 0:
        raise RuntimeError(
            "No se pueden migrar registros diarios sin un usuario propietario."
        )

    if first_user_row is None:
        return

    legacy_user_id = first_user_row["id"]


    connection.execute(
        """
        CREATE TABLE daily_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            steps INTEGER NOT NULL DEFAULT 0 CHECK (steps >= 0),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            UNIQUE (user_id, date)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO daily_logs_new (
            id,
            user_id,
            date,
            steps,
            notes,
            created_at
        )
        SELECT
            id,
            ?,
            date,
            steps,
            notes,
            created_at
        FROM daily_logs
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE daily_logs")
    connection.execute(
        "ALTER TABLE daily_logs_new RENAME TO daily_logs"
    )

def migrate_daily_recovery_logs_table(
    connection: sqlite3.Connection,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(daily_recovery_logs)"
        ).fetchall()
    }

    if "user_id" in columns:
        return

    first_user_row = connection.execute(
        """
        SELECT id
        FROM users
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()

    legacy_logs_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM daily_recovery_logs
        """
    ).fetchone()["count"]

    if first_user_row is None and legacy_logs_count > 0:
        raise RuntimeError(
            "No se pueden migrar registros de recuperación sin "
            "un usuario propietario."
        )

    if first_user_row is None:
        return

    legacy_user_id = first_user_row["id"]

    connection.execute(
        """
        CREATE TABLE daily_recovery_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            sleep_minutes INTEGER
                CHECK (sleep_minutes >= 0 AND sleep_minutes <= 1440),
            sleep_quality INTEGER
                CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
            is_rest_day INTEGER NOT NULL DEFAULT 0
                CHECK (is_rest_day IN (0, 1)),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            UNIQUE (user_id, date)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO daily_recovery_logs_new (
            id,
            user_id,
            date,
            sleep_minutes,
            sleep_quality,
            is_rest_day,
            notes,
            created_at
        )
        SELECT
            id,
            ?,
            date,
            sleep_minutes,
            sleep_quality,
            is_rest_day,
            notes,
            created_at
        FROM daily_recovery_logs
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE daily_recovery_logs")
    connection.execute(
        "ALTER TABLE daily_recovery_logs_new "
        "RENAME TO daily_recovery_logs"
    )

def get_legacy_user_id(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    empty_error_message: str,
) -> int | None:
    legacy_rows_count = connection.execute(
        f"SELECT COUNT(*) AS count FROM {table_name}"
    ).fetchone()["count"]

    first_user_row = connection.execute(
        """
        SELECT id
        FROM users
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()

    if first_user_row is None and legacy_rows_count > 0:
        raise RuntimeError(empty_error_message)

    if first_user_row is None:
        return None

    return first_user_row["id"]


def migrate_body_metrics_table(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(body_metrics)"
        ).fetchall()
    }

    if "user_id" in columns:
        return

    legacy_user_id = get_legacy_user_id(
        connection,
        table_name="body_metrics",
        empty_error_message=(
            "No se pueden migrar métricas corporales sin "
            "un usuario propietario."
        ),
    )

    if legacy_user_id is None:
        return

    connection.execute(
        """
        CREATE TABLE body_metrics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL CHECK (weight_kg > 0),
            height_cm REAL NOT NULL CHECK (height_cm > 0),
            bmi REAL NOT NULL CHECK (bmi > 0),
            body_fat_percentage REAL
                CHECK (
                    body_fat_percentage > 0
                    AND body_fat_percentage < 100
                ),
            waist_cm REAL CHECK (waist_cm > 0 AND waist_cm <= 300),
            hip_cm REAL CHECK (hip_cm > 0 AND hip_cm <= 300),
            chest_cm REAL CHECK (chest_cm > 0 AND chest_cm <= 300),
            arm_cm REAL CHECK (arm_cm > 0 AND arm_cm <= 200),
            thigh_cm REAL CHECK (thigh_cm > 0 AND thigh_cm <= 300),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            UNIQUE (user_id, date)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO body_metrics_new (
            id,
            user_id,
            date,
            weight_kg,
            height_cm,
            bmi,
            body_fat_percentage,
            waist_cm,
            hip_cm,
            chest_cm,
            arm_cm,
            thigh_cm,
            notes,
            created_at
        )
        SELECT
            id,
            ?,
            date,
            weight_kg,
            height_cm,
            bmi,
            body_fat_percentage,
            waist_cm,
            hip_cm,
            chest_cm,
            arm_cm,
            thigh_cm,
            notes,
            created_at
        FROM body_metrics
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE body_metrics")
    connection.execute(
        "ALTER TABLE body_metrics_new RENAME TO body_metrics"
    )


def migrate_runs_table(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(runs)"
        ).fetchall()
    }

    if "user_id" in columns:
        return

    legacy_user_id = get_legacy_user_id(
        connection,
        table_name="runs",
        empty_error_message=(
            "No se pueden migrar carreras sin un usuario propietario."
        ),
    )

    if legacy_user_id is None:
        return

    connection.execute(
        """
        CREATE TABLE runs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            distance_km REAL NOT NULL CHECK (distance_km > 0),
            duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
            average_pace_seconds_km REAL NOT NULL
                CHECK (average_pace_seconds_km > 0),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        INSERT INTO runs_new (
            id,
            user_id,
            date,
            distance_km,
            duration_seconds,
            average_pace_seconds_km,
            notes,
            created_at
        )
        SELECT
            id,
            ?,
            date,
            distance_km,
            duration_seconds,
            average_pace_seconds_km,
            notes,
            created_at
        FROM runs
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE runs")
    connection.execute("ALTER TABLE runs_new RENAME TO runs")
def migrate_workout_templates_table(
    connection: sqlite3.Connection,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(workout_templates)"
        ).fetchall()
    }

    if "user_id" in columns:
        return

    legacy_user_id = get_legacy_user_id(
        connection,
        table_name="workout_templates",
        empty_error_message=(
            "No se pueden migrar plantillas de entrenamiento sin "
            "un usuario propietario."
        ),
    )

    if legacy_user_id is None:
        return

    connection.execute(
        """
        CREATE TABLE workout_templates_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL CHECK (length(trim(name)) > 0),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        INSERT INTO workout_templates_new (
            id,
            user_id,
            name,
            notes,
            created_at
        )
        SELECT
            id,
            ?,
            name,
            notes,
            created_at
        FROM workout_templates
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE workout_templates")
    connection.execute(
        "ALTER TABLE workout_templates_new "
        "RENAME TO workout_templates"
    )

def migrate_body_composition_goals_table(
    connection: sqlite3.Connection,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(body_composition_goals)"
        ).fetchall()
    }

    if not columns or "user_id" in columns:
        return

    legacy_user_id = get_legacy_user_id(
        connection,
        table_name="body_composition_goals",
        empty_error_message=(
            "No se pueden migrar objetivos corporales sin "
            "un usuario propietario."
        ),
    )

    if legacy_user_id is None:
        return

    connection.execute(
        f"""
        CREATE TABLE body_composition_goals_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            metric_type TEXT NOT NULL CHECK (
                metric_type IN (
                    {BODY_COMPOSITION_GOAL_METRIC_TYPES_SQL}
                )
            ),
            target_value REAL NOT NULL CHECK (target_value > 0),
            direction TEXT NOT NULL CHECK (
                direction IN (
                    {BODY_COMPOSITION_GOAL_DIRECTIONS_SQL}
                )
            ),
            start_value REAL,
            started_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            UNIQUE (user_id, metric_type)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO body_composition_goals_new (
            id,
            user_id,
            metric_type,
            target_value,
            direction,
            start_value,
            started_at,
            created_at,
            updated_at
        )
        SELECT
            id,
            ?,
            metric_type,
            target_value,
            direction,
            start_value,
            started_at,
            created_at,
            updated_at
        FROM body_composition_goals
        """,
        (legacy_user_id,),
    )

    connection.execute("DROP TABLE body_composition_goals")
    connection.execute(
        "ALTER TABLE body_composition_goals_new "
        "RENAME TO body_composition_goals"
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
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                steps INTEGER NOT NULL DEFAULT 0 CHECK (steps >= 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, date)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_recovery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                sleep_minutes INTEGER
                    CHECK (sleep_minutes >= 0 AND sleep_minutes <= 1440),
                sleep_quality INTEGER
                    CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
                is_rest_day INTEGER NOT NULL DEFAULT 0
                    CHECK (is_rest_day IN (0, 1)),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, date)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS body_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                weight_kg REAL NOT NULL CHECK (weight_kg > 0),
                height_cm REAL NOT NULL CHECK (height_cm > 0),
                bmi REAL NOT NULL CHECK (bmi > 0),
                body_fat_percentage REAL
                    CHECK (
                        body_fat_percentage > 0
                        AND body_fat_percentage < 100
                    ),
                waist_cm REAL CHECK (waist_cm > 0 AND waist_cm <= 300),
                hip_cm REAL CHECK (hip_cm > 0 AND hip_cm <= 300),
                chest_cm REAL CHECK (chest_cm > 0 AND chest_cm <= 300),
                arm_cm REAL CHECK (arm_cm > 0 AND arm_cm <= 200),
                thigh_cm REAL CHECK (thigh_cm > 0 AND thigh_cm <= 300),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, date)
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
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
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
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                distance_km REAL NOT NULL CHECK (distance_km > 0),
                duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
                average_pace_seconds_km REAL NOT NULL
                    CHECK (average_pace_seconds_km > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
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
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
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
                user_id INTEGER NOT NULL,
                goal_type TEXT NOT NULL CHECK (
                    goal_type IN ({FITNESS_GOAL_TYPES_SQL})
                ),
                target_value REAL NOT NULL CHECK (target_value > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, goal_type)
            )
            """
        )

        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS body_composition_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                metric_type TEXT NOT NULL CHECK (
                    metric_type IN (
                        {BODY_COMPOSITION_GOAL_METRIC_TYPES_SQL}
                    )
                ),
                target_value REAL NOT NULL CHECK (target_value > 0),
                direction TEXT NOT NULL CHECK (
                    direction IN (
                        {BODY_COMPOSITION_GOAL_DIRECTIONS_SQL}
                    )
                ),
                start_value REAL,
                started_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, metric_type)
            )
            """
        )

        migrate_body_composition_goals_table(connection)

        migrate_fitness_goals_table(connection)
        migrate_daily_logs_table(connection)
        migrate_daily_recovery_logs_table(connection)
        migrate_body_metrics_table(connection)
        migrate_runs_table(connection)
        migrate_workout_templates_table(connection)

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_body_metrics_user_date
            ON body_metrics(user_id, date)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runs_user_date
            ON runs(user_id, date)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_workout_templates_user_id
            ON workout_templates(user_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_planned_workouts_user_date
            ON planned_workouts(user_id, scheduled_date)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_planned_workouts_user_status_date
            ON planned_workouts(user_id, status, scheduled_date)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS planned_workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                scheduled_date TEXT NOT NULL,
                workout_template_id INTEGER,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'planned'
                    CHECK (
                        status IN (
                            'planned',
                            'completed',
                            'skipped'
                        )
                    ),
                workout_session_id INTEGER UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (workout_template_id)
                    REFERENCES workout_templates(id)
                    ON DELETE SET NULL,
                FOREIGN KEY (workout_session_id)
                    REFERENCES workout_sessions(id)
                    ON DELETE SET NULL
            )
            """
        )
