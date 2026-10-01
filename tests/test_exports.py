import json
from datetime import datetime

from app.db import get_connection
from app.services.exports import create_data_export


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


def test_create_data_export_includes_nested_tracking_data(tmp_path):
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
                "2026-09-07",
                10000,
                "Paseo por la tarde.",
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
                user_id,
                "2026-09-07",
                75.5,
                180,
                23.3,
                "Medición matinal.",
            ),
        )

        session_cursor = connection.execute(
            """
            INSERT INTO workout_sessions (
                user_id,
                date,
                name,
                notes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                "2026-09-07",
                "Pierna",
                "Buen entrenamiento.",
            ),
        )

        exercise_cursor = connection.execute(
            """
            INSERT INTO workout_exercises (
                workout_session_id,
                name,
                muscle_group,
                position,
                technique_notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_cursor.lastrowid,
                "Sentadilla",
                "Cuádriceps",
                1,
                "Mantener la espalda recta.",
            ),
        )

        connection.execute(
            """
            INSERT INTO workout_sets (
                workout_exercise_id,
                set_type,
                position,
                target_rep_range,
                repetitions,
                weight_kg,
                rir,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exercise_cursor.lastrowid,
                "working",
                1,
                "8-10",
                8,
                100,
                2,
                "Controlar la bajada.",
            ),
        )

        connection.execute(
            """
            INSERT INTO runs (
                user_id,
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "2026-09-07",
                5,
                1500,
                300,
                "Carrera suave.",
            ),
        )

        nutrition_day_cursor = connection.execute(
            """
            INSERT INTO nutrition_days (
                user_id,
                date,
                notes
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                "2026-09-07",
                "Día equilibrado.",
            ),
        )
        meal_cursor = connection.execute(
            """
            INSERT INTO nutrition_meals (nutrition_day_id, name, position)
            VALUES (?, ?, ?)
            """,
            (nutrition_day_cursor.lastrowid, "Desayuno", 1),
        )

        connection.execute(
            """
            INSERT INTO nutrition_foods (
                nutrition_meal_id,
                name,
                quantity_g,
                calories,
                protein_g,
                carbs_g,
                fat_g,
                position,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meal_cursor.lastrowid,
                "Avena",
                80,
                300,
                10,
                50,
                6,
                1,
                "Con leche.",
            ),
        )

    export_path = create_data_export(
        user_id=user_id,
        exports_dir=tmp_path,
        now=datetime(2026, 9, 7, 13, 18, 0),
    )

    assert export_path == (
        tmp_path
        / f"fitness_tracker_export_2026-09-07_13-18-00_user{user_id}.json"
    )
    assert export_path.exists()

    export_data = json.loads(export_path.read_text(encoding="utf-8"))

    assert export_data["exported_at"] == "2026-09-07T13:18:00"
    assert len(export_data["daily_logs"]) == 1

    daily_log = export_data["daily_logs"][0]

    assert daily_log["date"] == "2026-09-07"
    assert daily_log["steps"] == 10000
    assert daily_log["notes"] == "Paseo por la tarde."
    assert export_data["body_metrics"][0]["weight_kg"] == 75.5
    assert export_data["runs"][0]["distance_km"] == 5.0

    session = export_data["workout_sessions"][0]

    assert session["name"] == "Pierna"
    assert session["exercises"][0]["name"] == "Sentadilla"
    assert session["exercises"][0]["sets"][0]["repetitions"] == 8

    nutrition_day = export_data["nutrition_days"][0]

    assert isinstance(nutrition_day["id"], int)
    assert nutrition_day["meals"][0]["name"] == "Desayuno"
    assert nutrition_day["meals"][0]["foods"][0]["name"] == "Avena"
    assert isinstance(nutrition_day["meals"][0]["id"], int)
    assert isinstance(nutrition_day["meals"][0]["foods"][0]["id"], int)


def insert_full_user_data(connection, *, email: str, label: str) -> int:
    user_id = connection.execute(
        "INSERT INTO users (email, display_name, password_hash) "
        "VALUES (?, ?, ?)",
        (email, label, "test-password-hash"),
    ).lastrowid

    connection.execute(
        "INSERT INTO daily_logs (user_id, date, steps, notes) "
        "VALUES (?, ?, ?, ?)",
        (user_id, "2026-09-07", 1000, f"pasos-{label}"),
    )
    connection.execute(
        "INSERT INTO body_metrics (user_id, date, weight_kg, height_cm, bmi, "
        "notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-09-07", 70, 175, 22.9, f"cuerpo-{label}"),
    )
    connection.execute(
        "INSERT INTO runs (user_id, date, distance_km, duration_seconds, "
        "average_pace_seconds_km, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-09-07", 5, 1500, 300, f"carrera-{label}"),
    )

    session_id = connection.execute(
        "INSERT INTO workout_sessions (user_id, date, name, notes) "
        "VALUES (?, ?, ?, ?)",
        (user_id, "2026-09-07", f"sesion-{label}", None),
    ).lastrowid
    exercise_id = connection.execute(
        "INSERT INTO workout_exercises (workout_session_id, name, "
        "muscle_group, position, technique_notes) VALUES (?, ?, ?, ?, ?)",
        (session_id, f"ejercicio-{label}", "pierna", 1, None),
    ).lastrowid
    connection.execute(
        "INSERT INTO workout_sets (workout_exercise_id, set_type, position, "
        "target_rep_range, repetitions, weight_kg, rir, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (exercise_id, "working", 1, "8-10", 8, 60, 2, f"serie-{label}"),
    )

    day_id = connection.execute(
        "INSERT INTO nutrition_days (user_id, date, notes) VALUES (?, ?, ?)",
        (user_id, "2026-09-07", f"dia-{label}"),
    ).lastrowid
    meal_id = connection.execute(
        "INSERT INTO nutrition_meals (nutrition_day_id, name, position) "
        "VALUES (?, ?, ?)",
        (day_id, f"comida-{label}", 1),
    ).lastrowid
    connection.execute(
        "INSERT INTO nutrition_foods (nutrition_meal_id, name, quantity_g, "
        "calories, protein_g, carbs_g, fat_g, position, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (meal_id, f"alimento-{label}", 100, 100, 5, 10, 1, 1, None),
    )

    return user_id


def test_create_data_export_contains_only_the_requested_users_data(
    tmp_path,
):
    with get_connection() as connection:
        alice_id = insert_full_user_data(
            connection, email="alice@example.com", label="alice",
        )
        bob_id = insert_full_user_data(
            connection, email="bob@example.com", label="bob",
        )

    alice_path = create_data_export(user_id=alice_id, exports_dir=tmp_path)
    alice_text = alice_path.read_text(encoding="utf-8")
    alice_data = json.loads(alice_text)

    # Nada de Bob en ninguna tabla, ni siquiera en las hijas anidadas.
    assert "bob" not in alice_text
    assert "alice" in alice_text
    assert len(alice_data["daily_logs"]) == 1
    assert len(alice_data["body_metrics"]) == 1
    assert len(alice_data["runs"]) == 1
    assert len(alice_data["workout_sessions"]) == 1
    assert len(alice_data["workout_sessions"][0]["exercises"]) == 1
    assert len(alice_data["workout_sessions"][0]["exercises"][0]["sets"]) == 1
    assert len(alice_data["nutrition_days"]) == 1
    assert len(alice_data["nutrition_days"][0]["meals"][0]["foods"]) == 1

    bob_path = create_data_export(user_id=bob_id, exports_dir=tmp_path)

    assert bob_path != alice_path
    assert "alice" not in bob_path.read_text(encoding="utf-8")
