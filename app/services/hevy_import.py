"""Importación de entrenamientos desde el CSV que exporta Hevy.

Hevy exporta una fila por serie con las columnas `title`, `start_time`,
`description`, `exercise_title`, `exercise_notes`, `set_index`, `set_type`,
`weight_kg` (o `weight_lbs`), `reps`, `rpe`, entre otras.
"""
from app.db import Connection
from app.services.workout_import import (
    InvalidImport,
    ParsedImport,
    RawSet,
    check_row_limit,
    clean,
    parse_number,
    parse_workout_date,
    plan_workouts,
    read_csv_rows,
    save_import,
    to_kg,
    DEFAULT_SESSION_NAME,
)

__all__ = ["InvalidImport", "parse_hevy_csv", "import_hevy_workouts", "parse_workout_date"]

REQUIRED_COLUMNS = ("title", "start_time", "exercise_title", "reps")
WEIGHT_COLUMNS = ("weight_kg", "weight_lbs")

SET_KINDS = {
    "": "working",
    "normal": "working",
    "failure": "failure",
    "warmup": "warmup",
    "warm_up": "warmup",
    "dropset": "drop_set",
    "drop_set": "drop_set",
}


def _raw_sets(content: bytes):
    reader = read_csv_rows(content)
    columns = set(reader.fieldnames or [])
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]

    if missing or not columns & set(WEIGHT_COLUMNS):
        raise InvalidImport(
            "No parece un CSV exportado de Hevy: faltan las columnas "
            + ", ".join(missing or ["weight_kg"])
            + "."
        )

    for row_number, row in enumerate(reader, start=2):
        check_row_limit(row_number)
        start_time = (row.get("start_time") or "").strip()
        workout_date = parse_workout_date(start_time)

        if workout_date is None:
            raise InvalidImport(
                f"Fecha no válida en la fila {row_number}: {start_time!r}. "
                "No se ha importado nada."
            )

        weight = parse_number(row.get("weight_kg"))

        if weight is None:
            weight = to_kg(parse_number(row.get("weight_lbs")), "lb")

        yield RawSet(
            row_number=row_number,
            title=clean(row.get("title"), 100) or DEFAULT_SESSION_NAME,
            workout_key=start_time,
            workout_date=workout_date,
            description=clean(row.get("description"), 1000) or None,
            exercise=clean(row.get("exercise_title"), 100),
            exercise_notes=clean(row.get("exercise_notes"), 1000) or None,
            kind=SET_KINDS.get((row.get("set_type") or "").strip().lower(), "working"),
            weight_kg=weight,
            reps=parse_number(row.get("reps")),
            rpe=parse_number(row.get("rpe")),
        )


def parse_hevy_csv(content: bytes) -> ParsedImport:
    return plan_workouts(_raw_sets(content))


def import_hevy_workouts(
    connection: Connection,
    user_id: int,
    content: bytes,
    *,
    dry_run: bool,
) -> dict:
    return save_import(
        connection, user_id, parse_hevy_csv(content), dry_run=dry_run,
    )
