"""Importación de entrenamientos desde el CSV que exporta Strong.

Strong exporta una fila por serie con las columnas `Date`, `Workout Name`,
`Duration`, `Exercise Name`, `Set Order`, `Weight`, `Reps`, `Distance`,
`Seconds`, `Notes`, `Workout Notes` y `RPE`. El peso no indica su unidad, así
que la elige quien importa.

`Set Order` es el número de la serie, o una letra para las especiales:
`W` calentamiento, `D` drop set y `F` al fallo. Las filas «Rest Timer» son
descansos, no series, y se ignoran.
"""
from app.db import Connection
from app.services.workout_import import (
    DEFAULT_SESSION_NAME,
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
)

__all__ = ["InvalidImport", "parse_strong_csv", "import_strong_workouts"]

REQUIRED_COLUMNS = ("date", "workout name", "exercise name", "reps", "weight")
WEIGHT_UNITS = ("kg", "lb")

SET_KINDS = {"w": "warmup", "d": "drop_set", "f": "failure"}


def _raw_sets(content: bytes, weight_unit: str):
    if weight_unit not in WEIGHT_UNITS:
        raise InvalidImport("La unidad de peso debe ser kg o lb.")

    reader = read_csv_rows(content)
    columns = set(reader.fieldnames or [])
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]

    if missing:
        raise InvalidImport(
            "No parece un CSV exportado de Strong: faltan las columnas "
            + ", ".join(missing)
            + "."
        )

    for row_number, row in enumerate(reader, start=2):
        check_row_limit(row_number)
        set_order = (row.get("set order") or "").strip().lower()

        if set_order == "rest timer":
            continue

        date_text = (row.get("date") or "").strip()
        workout_date = parse_workout_date(date_text)

        if workout_date is None:
            raise InvalidImport(
                f"Fecha no válida en la fila {row_number}: {date_text!r}. "
                "No se ha importado nada."
            )

        yield RawSet(
            row_number=row_number,
            title=clean(row.get("workout name"), 100) or DEFAULT_SESSION_NAME,
            workout_key=date_text,
            workout_date=workout_date,
            description=clean(row.get("workout notes"), 1000) or None,
            exercise=clean(row.get("exercise name"), 100),
            exercise_notes=clean(row.get("notes"), 1000) or None,
            kind=SET_KINDS.get(set_order, "working"),
            weight_kg=to_kg(parse_number(row.get("weight")), weight_unit),
            reps=parse_number(row.get("reps")),
            rpe=parse_number(row.get("rpe")),
        )


def parse_strong_csv(content: bytes, weight_unit: str = "kg") -> ParsedImport:
    return plan_workouts(_raw_sets(content, weight_unit))


def import_strong_workouts(
    connection: Connection,
    user_id: int,
    content: bytes,
    *,
    weight_unit: str = "kg",
    dry_run: bool,
) -> dict:
    return save_import(
        connection, user_id, parse_strong_csv(content, weight_unit),
        dry_run=dry_run,
    )
