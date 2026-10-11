import pytest

from app.db import IntegrityError, get_connection, initialize_database
from app.schema import TABLES
from tests.db_helpers import foreign_keys, table_columns, table_names

def test_initialize_database_creates_daily_logs_table():
    # Inicializo la base de datos
    initialize_database()
    # Obtengo una conexión a la base de datos
    with get_connection() as connection:
        assert "daily_logs" in table_names(connection)

def test_daily_logs_has_expected_columns():
    initialize_database()

    with get_connection() as connection:
        column_names = table_columns(connection, "daily_logs")

    assert column_names == {
        "id",
        "user_id",
        "date",
        "steps",
        "notes",
        "created_at",
    }


def test_initialize_database_is_idempotent_and_records_migrations():
    initialize_database()
    initialize_database()

    with get_connection() as connection:
        versions = [
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]

        assert versions == [1, 2]
        assert set(TABLES) <= set(table_names(connection))


def test_every_table_has_row_level_security_enabled():
    """La API REST pública de Supabase no debe poder leer ninguna tabla."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT relname, relrowsecurity FROM pg_class "
            "WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'"
        ).fetchall()

    without_rls = {
        row["relname"]
        for row in rows
        if not row["relrowsecurity"] and row["relname"] != "schema_migrations"
    }

    assert without_rls == set()


def test_initialize_database_creates_nutrition_tables():
    initialize_database()
    with get_connection() as connection:
        existing_tables = set(table_names(connection))

    assert {
        "nutrition_days",
        "nutrition_meals",
        "nutrition_foods",
    }.issubset(existing_tables)

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
        columns = table_columns(connection, table_name)

    assert columns == expected_columns

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
        references = foreign_keys(connection, table_name)

    assert any(
        foreign_key["from"] == "user_id"
        and foreign_key["table"] == "users"
        and foreign_key["on_delete"] == "CASCADE"
        for foreign_key in references
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

        with pytest.raises(IntegrityError):
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


def test_emails_are_unique_ignoring_case():
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (email, display_name, password_hash) "
            "VALUES (?, ?, ?)",
            ("Persona@Example.com", "Persona", "hash"),
        )

        with pytest.raises(IntegrityError):
            connection.execute(
                "INSERT INTO users (email, display_name, password_hash) "
                "VALUES (?, ?, ?)",
                ("persona@example.com", "Otra", "hash"),
            )


def test_a_failed_transaction_leaves_no_partial_changes():
    with pytest.raises(RuntimeError):
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (email, display_name, password_hash) "
                "VALUES (?, ?, ?)",
                ("rollback@example.com", "Rollback", "hash"),
            )
            raise RuntimeError("fallo a mitad")

    with get_connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()["total"] == 0


def test_lastrowid_rowcount_and_literal_percent_signs_work():
    with get_connection() as connection:
        user_id = connection.execute(
            "INSERT INTO users (email, display_name, password_hash) "
            "VALUES (?, ?, ?)",
            ("literal@example.com", "100% real? sí", "hash"),
        ).lastrowid

        assert isinstance(user_id, int)

        # `?` y `%` dentro de un literal o de un LIKE no se tocan.
        found = connection.execute(
            "SELECT id FROM users WHERE display_name LIKE '100%' "
            "AND display_name LIKE ?",
            ("%real?%",),
        ).fetchall()
        assert [row["id"] for row in found] == [user_id]

        updated = connection.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE id = ?",
            (user_id,),
        )
        assert updated.rowcount == 1


def test_current_timestamp_is_stored_in_the_text_format_the_app_expects():
    with get_connection() as connection:
        user_id = connection.execute(
            "INSERT INTO users (email, display_name, password_hash) "
            "VALUES (?, ?, ?)",
            ("ts@example.com", "TS", "hash"),
        ).lastrowid
        connection.execute(
            "UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        created_at = connection.execute(
            "SELECT created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()["created_at"]

    # "AAAA-MM-DD HH:MM:SS": lo que parsea la página de la cuenta.
    assert len(created_at) == 19 and created_at[10] == " "
