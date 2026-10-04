"""Restauración de los datos de UNA cuenta a partir de su exportación JSON.

Solo toca las filas de la cuenta indicada; el resto de usuarios no se ve
afectado. Los ids del fichero no se reutilizan: se generan nuevos y se
reasignan las relaciones (sesión → ejercicios → series, plantilla →
planificadas, etc.).

Una sección ausente en el fichero se deja como está; una sección presente
sustituye por completo a la actual (aunque venga vacía).
"""
from datetime import date

from app.db import Connection

from app.services.exports import EXPORT_FORMAT_VERSION


class InvalidExport(ValueError):
    pass


# Tablas raíz de la cuenta (user_id). Sus hijas se borran en cascada.
# sección -> (tabla, columnas, columnas de fecha)
ROOT_SECTIONS = {
    "daily_logs": (
        "daily_logs", ("date", "steps", "notes"), ("date",),
    ),
    "recovery_logs": (
        "daily_recovery_logs",
        ("date", "sleep_minutes", "sleep_quality", "is_rest_day", "notes"),
        ("date",),
    ),
    "body_metrics": (
        "body_metrics",
        (
            "date", "weight_kg", "height_cm", "bmi", "body_fat_percentage",
            "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm", "notes",
        ),
        ("date",),
    ),
    "runs": (
        "runs",
        (
            "date", "distance_km", "duration_seconds",
            "average_pace_seconds_km", "notes",
        ),
        ("date",),
    ),
    "fitness_goals": (
        "fitness_goals", ("goal_type", "target_value"), (),
    ),
    "body_composition_goals": (
        "body_composition_goals",
        (
            "metric_type", "target_value", "direction", "start_value",
            "started_at",
        ),
        ("started_at",),
    ),
    "food_library": (
        "food_library",
        (
            "name", "calories_per_100g", "protein_per_100g",
            "carbs_per_100g", "fat_per_100g", "notes",
        ),
        (),
    ),
}

WORKOUT_EXERCISE_COLUMNS = (
    "name", "muscle_group", "position", "technique_notes",
)
WORKOUT_SET_COLUMNS = (
    "set_type", "position", "target_rep_range", "repetitions",
    "weight_kg", "rir", "notes",
)
NUTRITION_FOOD_COLUMNS = (
    "name", "quantity_g", "calories", "protein_g", "carbs_g", "fat_g",
    "position", "notes",
)
MEAL_ITEM_COLUMNS = (
    "name", "quantity_g", "calories_per_100g", "protein_per_100g",
    "carbs_per_100g", "fat_per_100g", "position", "notes",
)

# Orden de borrado: las planificadas primero (referencian plantillas/sesiones).
DELETE_ORDER = (
    ("planned_workouts", "planned_workouts"),
    ("daily_logs", "daily_logs"),
    ("recovery_logs", "daily_recovery_logs"),
    ("body_metrics", "body_metrics"),
    ("runs", "runs"),
    ("workout_sessions", "workout_sessions"),
    ("nutrition_days", "nutrition_days"),
    ("fitness_goals", "fitness_goals"),
    ("body_composition_goals", "body_composition_goals"),
    ("workout_templates", "workout_templates"),
    ("food_library", "food_library"),
    ("meal_templates", "meal_templates"),
)


def _row(record, columns, date_columns=(), where="registro"):
    if not isinstance(record, dict):
        raise InvalidExport(f"Cada {where} debe ser un objeto.")

    values = []

    for column in columns:
        value = record.get(column)

        if isinstance(value, (dict, list)):
            raise InvalidExport(f"Valor no válido en «{column}».")

        if column in date_columns:
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError) as error:
                raise InvalidExport(
                    f"Fecha no válida en «{column}»: {value!r}."
                ) from error

        values.append(value)

    return values


def _list(data: dict, key: str):
    value = data.get(key)

    if value is None:
        return None

    if not isinstance(value, list):
        raise InvalidExport(f"«{key}» debe ser una lista.")

    return value


def _insert(connection, table, owner_column, owner_id, columns, values):
    placeholders = ", ".join("?" for _ in range(len(columns) + 1))
    cursor = connection.execute(
        f"INSERT INTO {table} ({owner_column}, {', '.join(columns)}) "
        f"VALUES ({placeholders})",
        (owner_id, *values),
    )

    return cursor.lastrowid


def _insert_children(
    connection, table, parent_column, parent_id, columns, records, where,
):
    for record in records or []:
        _insert(
            connection, table, parent_column, parent_id, columns,
            _row(record, columns, where=where),
        )


def restore_account_data(
    connection: Connection,
    user_id: int,
    data,
) -> dict[str, int]:
    """Aplica la exportación dentro de la transacción de `connection`.

    Lanza InvalidExport o IntegrityError; quien llama debe revertir.
    """
    if not isinstance(data, dict) or "exported_at" not in data:
        raise InvalidExport("El archivo no es una exportación de Fitness Tracker.")

    version = data.get("format_version", 1)

    if not isinstance(version, int) or not 1 <= version <= EXPORT_FORMAT_VERSION:
        raise InvalidExport("La versión del archivo no es compatible.")

    sections = {
        key: _list(data, key)
        for key in (
            *ROOT_SECTIONS, "workout_sessions", "nutrition_days",
            "workout_templates", "planned_workouts", "meal_templates",
        )
    }

    if all(value is None for value in sections.values()):
        raise InvalidExport("El archivo no contiene ningún dato que restaurar.")

    # Primero se borra lo de las secciones presentes.
    for key, table in DELETE_ORDER:
        if sections.get(key) is not None:
            connection.execute(
                f"DELETE FROM {table} WHERE user_id = ?", (user_id,),
            )

    counts: dict[str, int] = {}

    for key, (table, columns, date_columns) in ROOT_SECTIONS.items():
        records = sections[key]

        if records is None:
            continue

        for record in records:
            _insert(
                connection, table, "user_id", user_id, columns,
                _row(record, columns, date_columns, key),
            )

        counts[key] = len(records)

    session_ids: dict[int, int] = {}

    if sections["workout_sessions"] is not None:
        for session in sections["workout_sessions"]:
            values = _row(
                session, ("date", "name", "notes"), ("date",), "sesión",
            )
            new_session_id = _insert(
                connection, "workout_sessions", "user_id", user_id,
                ("date", "name", "notes"), values,
            )

            if isinstance(session.get("id"), int):
                session_ids[session["id"]] = new_session_id

            for exercise in session.get("exercises") or []:
                new_exercise_id = _insert(
                    connection, "workout_exercises", "workout_session_id",
                    new_session_id, WORKOUT_EXERCISE_COLUMNS,
                    _row(exercise, WORKOUT_EXERCISE_COLUMNS, where="ejercicio"),
                )
                _insert_children(
                    connection, "workout_sets", "workout_exercise_id",
                    new_exercise_id, WORKOUT_SET_COLUMNS,
                    exercise.get("sets"), "serie",
                )

        counts["workout_sessions"] = len(sections["workout_sessions"])

    if sections["nutrition_days"] is not None:
        for day in sections["nutrition_days"]:
            new_day_id = _insert(
                connection, "nutrition_days", "user_id", user_id,
                ("date", "notes"),
                _row(day, ("date", "notes"), ("date",), "día"),
            )

            for meal in day.get("meals") or []:
                new_meal_id = _insert(
                    connection, "nutrition_meals", "nutrition_day_id",
                    new_day_id, ("name", "position"),
                    _row(meal, ("name", "position"), where="comida"),
                )
                _insert_children(
                    connection, "nutrition_foods", "nutrition_meal_id",
                    new_meal_id, NUTRITION_FOOD_COLUMNS,
                    meal.get("foods"), "alimento",
                )

        counts["nutrition_days"] = len(sections["nutrition_days"])

    template_ids: dict[int, int] = {}

    if sections["workout_templates"] is not None:
        for template in sections["workout_templates"]:
            new_template_id = _insert(
                connection, "workout_templates", "user_id", user_id,
                ("name", "notes"),
                _row(template, ("name", "notes"), where="plantilla"),
            )

            if isinstance(template.get("id"), int):
                template_ids[template["id"]] = new_template_id

            for exercise in template.get("exercises") or []:
                new_exercise_id = _insert(
                    connection, "workout_template_exercises",
                    "workout_template_id", new_template_id,
                    WORKOUT_EXERCISE_COLUMNS,
                    _row(exercise, WORKOUT_EXERCISE_COLUMNS, where="ejercicio"),
                )
                _insert_children(
                    connection, "workout_template_sets",
                    "workout_template_exercise_id", new_exercise_id,
                    WORKOUT_SET_COLUMNS, exercise.get("sets"), "serie",
                )

        counts["workout_templates"] = len(sections["workout_templates"])

    if sections["meal_templates"] is not None:
        for meal_template in sections["meal_templates"]:
            new_id = _insert(
                connection, "meal_templates", "user_id", user_id,
                ("name", "notes"),
                _row(meal_template, ("name", "notes"), where="plantilla"),
            )
            _insert_children(
                connection, "meal_template_items", "meal_template_id",
                new_id, MEAL_ITEM_COLUMNS, meal_template.get("items"),
                "elemento",
            )

        counts["meal_templates"] = len(sections["meal_templates"])

    if sections["planned_workouts"] is not None:
        for planned in sections["planned_workouts"]:
            values = _row(
                planned,
                ("scheduled_date", "name", "notes", "status"),
                ("scheduled_date",),
                "sesión planificada",
            )
            connection.execute(
                """
                INSERT INTO planned_workouts (
                    user_id, scheduled_date, name, notes, status,
                    workout_template_id, workout_session_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, *values,
                    template_ids.get(planned.get("workout_template_id")),
                    session_ids.get(planned.get("workout_session_id")),
                ),
            )

        counts["planned_workouts"] = len(sections["planned_workouts"])

    return counts
