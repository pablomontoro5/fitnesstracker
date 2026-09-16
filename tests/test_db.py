import pytest
from app.db import DATABASE_PATH, get_connection, initialize_database

def test_initialize_database_creates_daily_logs_table():
    # Inicializo la base de datos
    initialize_database()
    # Obtengo una conexión a la base de datos
    with get_connection() as connection:
        table=connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_logs';").fetchone()
        assert table is not None, "La tabla 'daily_logs' no fue creada en la base de datos."

def test_daily_logs_has_expected_columns():
    initialize_database()

    with get_connection() as connection:
        columns = connection.execute(
            "PRAGMA table_info(daily_logs)"
        ).fetchall()

    column_names = {column["name"] for column in columns}

    assert column_names == {
        "id",
        "user_id",
        "date",
        "steps",
        "notes",
        "created_at",
    }


def test_database_file_is_created():
    initialize_database()

    assert DATABASE_PATH.exists()


def test_initialize_database_creates_nutrition_tables():
    initialize_database()
    with get_connection() as connection:
        table_names = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert {
        "nutrition_days",
        "nutrition_meals",
        "nutrition_foods",
    }.issubset(table_names)

@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    [
        (
            "body_metrics",
            {
                "id",
                "user_id",
                "date",
                "weight_kg",
                "height_cm",
                "bmi",
                "body_fat_percentage",
                "waist_cm",
                "hip_cm",
                "chest_cm",
                "arm_cm",
                "thigh_cm",
                "notes",
                "created_at",
            },
        ),
        (
            "runs",
            {
                "id",
                "user_id",
                "date",
                "distance_km",
                "duration_seconds",
                "average_pace_seconds_km",
                "notes",
                "created_at",
            },
        ),
        (
            "workout_sessions",
            {
                "id",
                "user_id",
                "date",
                "name",
                "notes",
                "created_at",
            },
        ),
    ],
)
def test_user_owned_tracking_tables_have_expected_columns(
    table_name: str,
    expected_columns: set[str],
):
    initialize_database()

    with get_connection() as connection:
        columns = connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

    assert {column["name"] for column in columns} == expected_columns

@pytest.mark.parametrize(
    "table_name",
    [
        "body_metrics",
        "runs",
        "workout_sessions",
    ],
)
def test_user_owned_tracking_tables_reference_users(table_name: str):
    initialize_database()

    with get_connection() as connection:
        foreign_keys = connection.execute(
            f"PRAGMA foreign_key_list({table_name})"
        ).fetchall()

    assert any(
        foreign_key["from"] == "user_id"
        and foreign_key["table"] == "users"
        and foreign_key["to"] == "id"
        and foreign_key["on_delete"].upper() == "CASCADE"
        for foreign_key in foreign_keys
    )

def test_body_metrics_date_is_unique_per_user():
    initialize_database()

    with get_connection() as connection:
        first_user_id = connection.execute(
            """
            INSERT INTO users (
                email,
                display_name,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (
                "first-body-owner@example.com",
                "First body owner",
                "test-password-hash",
            ),
        ).lastrowid

        second_user_id = connection.execute(
            """
            INSERT INTO users (
                email,
                display_name,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (
                "second-body-owner@example.com",
                "Second body owner",
                "test-password-hash",
            ),
        ).lastrowid

        body_metric_values = (
            "2026-09-01",
            80,
            180,
            24.69,
            None,
        )

        connection.execute(
            """
            INSERT INTO body_metrics (
                user_id,
                date,
                weight_kg,
                height_cm,
                bmi,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                first_user_id,
                *body_metric_values,
            ),
        )

        connection.execute(
            """
            INSERT INTO body_metrics (
                user_id,
                date,
                weight_kg,
                height_cm,
                bmi,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                second_user_id,
                *body_metric_values,
            ),
        )

        with pytest.raises(
            Exception,
            match="UNIQUE constraint failed",
        ):
            connection.execute(
                """
                INSERT INTO body_metrics (
                    user_id,
                    date,
                    weight_kg,
                    height_cm,
                    bmi,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    first_user_id,
                    *body_metric_values,
                ),
            )    