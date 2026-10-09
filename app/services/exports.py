import json
import tempfile
from datetime import datetime
from pathlib import Path

from app.db import get_connection


# Fichero temporal que se borra tras la descarga. Va al directorio temporal del
# sistema, que siempre existe y es escribible (también en el contenedor, donde
# la aplicación no guarda nada en disco).
EXPORTS_DIR = Path(tempfile.gettempdir()) / "fitness-tracker-exports"

# Versión del formato. La restauración por cuenta la comprueba.
EXPORT_FORMAT_VERSION = 2


def fetch_rows(connection, query: str, params: tuple) -> list[dict]:
    return [row_to_dict(row) for row in connection.execute(query, params)]


def group_children(rows: list[dict], parent_key: str) -> dict[int, list[dict]]:
    """Agrupa filas hijas por su id de padre, quitando la clave del padre."""
    grouped: dict[int, list[dict]] = {}

    for row in rows:
        grouped.setdefault(row[parent_key], []).append(
            {key: value for key, value in row.items() if key != parent_key}
        )

    return grouped


def row_to_dict(row) -> dict:
    return dict(row)


def create_data_export(
    user_id: int,
    exports_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Exporta únicamente los datos de la cuenta indicada."""
    export_directory = exports_dir or EXPORTS_DIR
    # Solo el propietario: la exportación contiene datos de salud.
    export_directory.mkdir(mode=0o700, parents=True, exist_ok=True)

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
                SELECT
                    id, date, weight_kg, height_cm, bmi,
                    body_fat_percentage, waist_cm, hip_cm,
                    chest_cm, arm_cm, thigh_cm, notes
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

        recovery_logs = fetch_rows(
            connection,
            """
            SELECT id, date, sleep_minutes, sleep_quality, is_rest_day, notes
            FROM daily_recovery_logs
            WHERE user_id = ?
            ORDER BY date ASC, id ASC
            """,
            (user_id,),
        )

        fitness_goals = fetch_rows(
            connection,
            """
            SELECT id, goal_type, target_value
            FROM fitness_goals
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        )

        body_composition_goals = fetch_rows(
            connection,
            """
            SELECT
                id, metric_type, target_value, direction,
                start_value, started_at
            FROM body_composition_goals
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        )

        workout_templates = fetch_rows(
            connection,
            """
            SELECT id, name, notes
            FROM workout_templates
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        )

        template_exercises = fetch_rows(
            connection,
            """
            SELECT
                id, workout_template_id, name, muscle_group,
                position, technique_notes
            FROM workout_template_exercises
            WHERE workout_template_id IN (
                SELECT id FROM workout_templates WHERE user_id = ?
            )
            ORDER BY workout_template_id ASC, position ASC, id ASC
            """,
            (user_id,),
        )

        template_sets = fetch_rows(
            connection,
            """
            SELECT
                id, workout_template_exercise_id, set_type, position,
                target_rep_range, repetitions, weight_kg, rir, notes
            FROM workout_template_sets
            WHERE workout_template_exercise_id IN (
                SELECT exercise.id
                FROM workout_template_exercises AS exercise
                JOIN workout_templates AS template
                    ON template.id = exercise.workout_template_id
                WHERE template.user_id = ?
            )
            ORDER BY workout_template_exercise_id ASC, position ASC, id ASC
            """,
            (user_id,),
        )

        planned_workouts = fetch_rows(
            connection,
            """
            SELECT
                id, scheduled_date, workout_template_id, name, notes,
                status, workout_session_id
            FROM planned_workouts
            WHERE user_id = ?
            ORDER BY scheduled_date ASC, id ASC
            """,
            (user_id,),
        )

        food_library = fetch_rows(
            connection,
            """
            SELECT
                id, name, calories_per_100g, protein_per_100g,
                carbs_per_100g, fat_per_100g, notes
            FROM food_library
            WHERE user_id = ?
            ORDER BY name ASC, id ASC
            """,
            (user_id,),
        )

        meal_templates = fetch_rows(
            connection,
            """
            SELECT id, name, notes
            FROM meal_templates
            WHERE user_id = ?
            ORDER BY name ASC, id ASC
            """,
            (user_id,),
        )

        meal_template_items = fetch_rows(
            connection,
            """
            SELECT
                id, meal_template_id, name, quantity_g,
                calories_per_100g, protein_per_100g, carbs_per_100g,
                fat_per_100g, position, notes
            FROM meal_template_items
            WHERE meal_template_id IN (
                SELECT id FROM meal_templates WHERE user_id = ?
            )
            ORDER BY meal_template_id ASC, position ASC, id ASC
            """,
            (user_id,),
        )

    sets_by_template_exercise_id = group_children(
        template_sets,
        "workout_template_exercise_id",
    )
    template_exercises_by_template_id = group_children(
        [
            exercise
            | {"sets": sets_by_template_exercise_id.get(exercise["id"], [])}
            for exercise in template_exercises
        ],
        "workout_template_id",
    )
    items_by_meal_template_id = group_children(
        meal_template_items,
        "meal_template_id",
    )

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
        "format_version": EXPORT_FORMAT_VERSION,
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
        "recovery_logs": recovery_logs,
        "fitness_goals": fitness_goals,
        "body_composition_goals": body_composition_goals,
        "workout_templates": [
            template
            | {
                "exercises": template_exercises_by_template_id.get(
                    template["id"],
                    [],
                )
            }
            for template in workout_templates
        ],
        "planned_workouts": planned_workouts,
        "food_library": food_library,
        "meal_templates": [
            meal_template
            | {"items": items_by_meal_template_id.get(meal_template["id"], [])}
            for meal_template in meal_templates
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