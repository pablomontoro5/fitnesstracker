import json
from datetime import datetime
from pathlib import Path

from app.db import DATA_DIR, get_connection


EXPORTS_DIR = DATA_DIR / "exports"


def row_to_dict(row) -> dict:
    return dict(row)


def create_data_export(
    user_id: int,
    exports_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Exporta únicamente los datos de la cuenta indicada."""
    export_directory = exports_dir or EXPORTS_DIR
    export_directory.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        daily_logs = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT id, date, steps, notes
                FROM daily_logs
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        body_metrics = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT id, date, weight_kg, height_cm, bmi, notes
                FROM body_metrics
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        runs = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT
                    id,
                    date,
                    distance_km,
                    duration_seconds,
                    average_pace_seconds_km,
                    notes
                FROM runs
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        workout_sessions = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT id, date, name, notes
                FROM workout_sessions
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        workout_exercises = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT
                    id,
                    workout_session_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                FROM workout_exercises
                WHERE workout_session_id IN (
                    SELECT id
                    FROM workout_sessions
                    WHERE user_id = ?
                )
                ORDER BY workout_session_id ASC, position ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        workout_sets = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT
                    id,
                    workout_exercise_id,
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                FROM workout_sets
                WHERE workout_exercise_id IN (
                    SELECT exercise.id
                    FROM workout_exercises AS exercise
                    JOIN workout_sessions AS session
                        ON session.id = exercise.workout_session_id
                    WHERE session.user_id = ?
                )
                ORDER BY workout_exercise_id ASC, position ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        nutrition_days = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT id, date, notes
                FROM nutrition_days
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        nutrition_meals = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT id, nutrition_day_id, name, position
                FROM nutrition_meals
                WHERE nutrition_day_id IN (
                    SELECT id
                    FROM nutrition_days
                    WHERE user_id = ?
                )
                ORDER BY nutrition_day_id ASC, position ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

        nutrition_foods = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT
                    id,
                    nutrition_meal_id,
                    name,
                    quantity_g,
                    calories,
                    protein_g,
                    carbs_g,
                    fat_g,
                    position,
                    notes
                FROM nutrition_foods
                WHERE nutrition_meal_id IN (
                    SELECT meal.id
                    FROM nutrition_meals AS meal
                    JOIN nutrition_days AS day
                        ON day.id = meal.nutrition_day_id
                    WHERE day.user_id = ?
                )
                ORDER BY nutrition_meal_id ASC, position ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        ]

    sets_by_exercise_id = {}
    for workout_set in workout_sets:
        sets_by_exercise_id.setdefault(
            workout_set["workout_exercise_id"],
            [],
        ).append(
            {
                key: value
                for key, value in workout_set.items()
                if key != "workout_exercise_id"
            }
        )

    exercises_by_session_id = {}
    for exercise in workout_exercises:
        exercise_id = exercise["id"]

        exercises_by_session_id.setdefault(
            exercise["workout_session_id"],
            [],
        ).append(
            {
                key: value
                for key, value in exercise.items()
                if key != "workout_session_id"
            }
            | {"sets": sets_by_exercise_id.get(exercise_id, [])}
        )

    meals_by_day_id = {}
    for meal in nutrition_meals:
        meals_by_day_id.setdefault(
            meal["nutrition_day_id"],
            [],
        ).append(
            {
                key: value
                for key, value in meal.items()
                if key != "nutrition_day_id"
            }
            | {
                "foods": [
                    {
                        key: value
                        for key, value in food.items()
                        if key != "nutrition_meal_id"
                    }
                    for food in nutrition_foods
                    if food["nutrition_meal_id"] == meal["id"]
                ]
            }
        )

    export_data = {
        "exported_at": (now or datetime.now()).isoformat(timespec="seconds"),
        "daily_logs": daily_logs,
        "body_metrics": body_metrics,
        "workout_sessions": [
            session | {
                "exercises": exercises_by_session_id.get(
                    session["id"],
                    [],
                )
            }
            for session in workout_sessions
        ],
        "runs": runs,
        "nutrition_days": [
            nutrition_day | {
                "meals": meals_by_day_id.get(
                    nutrition_day["id"],
                    [],
                )
            }
            for nutrition_day in nutrition_days
        ],
    }

    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    # El id de usuario evita que dos exportaciones simultáneas compartan
    # fichero y que una cuenta reciba los datos de otra.
    export_path = (
        export_directory
        / f"fitness_tracker_export_{timestamp}_user{user_id}.json"
    )

    with export_path.open("w", encoding="utf-8") as export_file:
        json.dump(
            export_data,
            export_file,
            ensure_ascii=False,
            indent=2,
        )
        export_file.write("\n")

    return export_path