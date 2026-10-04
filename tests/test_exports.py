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

    connection.execute(
        "INSERT INTO daily_recovery_logs (user_id, date, sleep_minutes, "
        "sleep_quality, is_rest_day, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-09-07", 450, 4, 1, f"recuperacion-{label}"),
    )
    connection.execute(
        "INSERT INTO fitness_goals (user_id, goal_type, target_value) "
        "VALUES (?, ?, ?)",
        (user_id, "daily_steps", 9000),
    )
    connection.execute(
        "INSERT INTO body_composition_goals (user_id, metric_type, "
        "target_value, direction, start_value, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "weight_kg", 68, "decrease", 72, "2026-09-01"),
    )

    template_id = connection.execute(
        "INSERT INTO workout_templates (user_id, name, notes) "
        "VALUES (?, ?, ?)",
        (user_id, f"plantilla-{label}", None),
    ).lastrowid
    template_exercise_id = connection.execute(
        "INSERT INTO workout_template_exercises (workout_template_id, name, "
        "muscle_group, position, technique_notes) VALUES (?, ?, ?, ?, ?)",
        (template_id, f"press-{label}", "pecho", 1, None),
    ).lastrowid
    connection.execute(
        "INSERT INTO workout_template_sets (workout_template_exercise_id, "
        "set_type, position, target_rep_range, repetitions, weight_kg, rir, "
        "notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (template_exercise_id, "working", 1, "6-8", 6, 50, 2, None),
    )
    connection.execute(
        "INSERT INTO planned_workouts (user_id, scheduled_date, "
        "workout_template_id, name, notes, status, workout_session_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            user_id, "2026-09-10", template_id, f"plan-{label}", None,
            "completed", session_id,
        ),
    )

    connection.execute(
        "INSERT INTO food_library (user_id, name, calories_per_100g, "
        "protein_per_100g, carbs_per_100g, fat_per_100g, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, f"arroz-{label}", 130, 2.7, 28, 0.3, None),
    )
    meal_template_id = connection.execute(
        "INSERT INTO meal_templates (user_id, name, notes) VALUES (?, ?, ?)",
        (user_id, f"desayuno-{label}", None),
    ).lastrowid
    connection.execute(
        "INSERT INTO meal_template_items (meal_template_id, name, "
        "quantity_g, calories_per_100g, protein_per_100g, carbs_per_100g, "
        "fat_per_100g, position, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (meal_template_id, f"avena-{label}", 50, 370, 13, 60, 7, 1, None),
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


def test_export_includes_every_user_owned_table(tmp_path):
    with get_connection() as connection:
        user_id = insert_full_user_data(
            connection, email="full@example.com", label="full",
        )

    data = json.loads(
        create_data_export(user_id=user_id, exports_dir=tmp_path).read_text(
            encoding="utf-8"
        )
    )

    assert data["format_version"] == 2
    assert data["recovery_logs"][0]["sleep_minutes"] == 450
    assert data["fitness_goals"] == [
        {"id": data["fitness_goals"][0]["id"],
         "goal_type": "daily_steps", "target_value": 9000}
    ]
    assert data["body_composition_goals"][0]["direction"] == "decrease"

    template = data["workout_templates"][0]
    assert template["name"] == "plantilla-full"
    assert template["exercises"][0]["sets"][0]["target_rep_range"] == "6-8"

    planned = data["planned_workouts"][0]
    assert planned["status"] == "completed"
    assert planned["workout_template_id"] == template["id"]
    assert planned["workout_session_id"] == data["workout_sessions"][0]["id"]

    assert data["food_library"][0]["name"] == "arroz-full"
    assert data["meal_templates"][0]["items"][0]["name"] == "avena-full"
    assert "meal_template_id" not in data["meal_templates"][0]["items"][0]


def test_export_covers_all_tables_that_belong_to_a_user():
    """Si alguien añade una tabla con datos de usuario y no la exporta,
    este test falla en lugar de perder datos en silencio."""
    exported_tables = {
        "daily_logs", "daily_recovery_logs", "body_metrics",
        "workout_sessions", "workout_exercises", "workout_sets", "runs",
        "nutrition_days", "nutrition_meals", "nutrition_foods",
        "food_library", "meal_templates", "meal_template_items",
        "workout_templates", "workout_template_exercises",
        "workout_template_sets", "fitness_goals",
        "body_composition_goals", "planned_workouts",
    }
    # Datos de la instalación o de la cuenta que no son contenido del usuario.
    not_exported = {"users", "password_resets", "invitations", "schema_migrations"}

    with get_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT table_name AS name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        }

    assert tables - not_exported == exported_tables
