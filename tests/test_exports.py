import json
from datetime import datetime

from app.db import get_connection
from app.services.exports import create_data_export


def test_create_data_export_includes_nested_tracking_data(tmp_path):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO daily_logs (date, steps, notes)
            VALUES (?, ?, ?)
            """,
            ("2026-09-07", 10000, "Paseo por la tarde."),
        )

        connection.execute(
            """
            INSERT INTO body_metrics (
                date,
                weight_kg,
                height_cm,
                bmi,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-09-07", 75.5, 180, 23.3, "Medición matinal."),
        )

        session_cursor = connection.execute(
            """
            INSERT INTO workout_sessions (date, name, notes)
            VALUES (?, ?, ?)
            """,
            ("2026-09-07", "Pierna", "Buen entrenamiento."),
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
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-09-07", 5, 1500, 300, "Carrera suave."),
        )

        nutrition_day_cursor = connection.execute(
            """
            INSERT INTO nutrition_days (date, notes)
            VALUES (?, ?)
            """,
            ("2026-09-07", "Día equilibrado."),
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
        exports_dir=tmp_path,
        now=datetime(2026, 9, 7, 13, 18, 0),
    )

    assert export_path == (
        tmp_path / "fitness_tracker_export_2026-09-07_13-18-00.json"
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