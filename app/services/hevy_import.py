"""Importación de entrenamientos desde el CSV que exporta Hevy.

Hevy exporta una fila por serie con las columnas `title`, `start_time`,
`description`, `exercise_title`, `exercise_notes`, `set_index`, `set_type`,
`weight_kg` (o `weight_lbs`), `reps`, `rpe`, entre otras. Este módulo las
convierte en sesiones, ejercicios y series de la aplicación.

La importación solo AÑADE datos y es repetible: una sesión con la misma fecha y
el mismo nombre que otra ya existente de la cuenta se omite.
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from app.db import Connection


MAX_ROWS = 100_000
MAX_WARNINGS_SHOWN = 10
LBS_TO_KG = 0.45359237
UNCLASSIFIED_MUSCLE_GROUP = "Sin clasificar"
DEFAULT_SESSION_NAME = "Entrenamiento"

REQUIRED_COLUMNS = ("title", "start_time", "exercise_title", "reps")
WEIGHT_COLUMNS = ("weight_kg", "weight_lbs")

SET_TYPES = {
    "": "working",
    "normal": "working",
    "failure": "working",
    "warmup": "warmup",
    "warm_up": "warmup",
    "dropset": "drop_set",
    "drop_set": "drop_set",
}

MONTHS = {
    name: number
    for number, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"),
        start=1,
    )
}
_HEVY_DATE_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]{3})[A-Za-z]*\.?\s+(\d{4})")


class InvalidImport(ValueError):
    """El archivo no se puede importar; el mensaje se muestra al usuario."""


@dataclass
class SetPlan:
    set_type: str
    repetitions: int
    weight_kg: float
    rir: float | None
    notes: str | None


@dataclass
class ExercisePlan:
    name: str
    technique_notes: str | None
    sets: list[SetPlan] = field(default_factory=list)


@dataclass
class WorkoutPlan:
    date: str
    name: str
    notes: str | None
    exercises: list[ExercisePlan] = field(default_factory=list)


@dataclass
class ParsedImport:
    workouts: list[WorkoutPlan]
    omitted_sets: int
    warnings: list[str]


def _clean(value, limit: int) -> str:
    return (value or "").strip()[:limit]


def _number(text) -> float | None:
    text = (text or "").strip()

    if not text:
        return None

    if "," in text and "." not in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def parse_workout_date(text: str) -> str | None:
    """Fecha (AAAA-MM-DD) de `start_time`; admite «18 Oct 2023, 18:03» e ISO."""
    text = (text or "").strip()
    match = _HEVY_DATE_RE.match(text)

    if match:
        day, month_name, year = match.groups()
        month = MONTHS.get(month_name.lower())

        if month is None:
            return None

        try:
            return date(int(year), month, int(day)).isoformat()
        except ValueError:
            return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _read_rows(content: bytes) -> csv.DictReader:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidImport(
            "El archivo debe estar codificado en UTF-8 (el CSV original de Hevy)."
        ) from error

    first_line = text.splitlines()[0] if text.strip() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    reader.fieldnames = [
        (name or "").strip().lower() for name in (reader.fieldnames or [])
    ]

    return reader


def parse_hevy_csv(content: bytes) -> ParsedImport:
    reader = _read_rows(content)
    columns = set(reader.fieldnames or [])
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]

    if missing or not columns & set(WEIGHT_COLUMNS):
        raise InvalidImport(
            "No parece un CSV exportado de Hevy: faltan las columnas "
            + ", ".join(missing or ["weight_kg"])
            + "."
        )

    workouts: dict[tuple[str, str], WorkoutPlan] = {}
    last_exercise: dict[tuple[str, str], ExercisePlan] = {}
    omitted = 0
    warnings: list[str] = []

    for row_number, row in enumerate(reader, start=2):
        if row_number > MAX_ROWS + 1:
            raise InvalidImport(
                f"El archivo tiene demasiadas filas (máximo {MAX_ROWS})."
            )

        title = _clean(row.get("title"), 100) or DEFAULT_SESSION_NAME
        start_time = (row.get("start_time") or "").strip()
        workout_date = parse_workout_date(start_time)

        if workout_date is None:
            raise InvalidImport(
                f"Fecha no válida en la fila {row_number}: {start_time!r}. "
                "No se ha importado nada."
            )

        key = (title, start_time)

        if key not in workouts:
            workouts[key] = WorkoutPlan(
                date=workout_date,
                name=title,
                notes=_clean(row.get("description"), 1000) or None,
            )

        workout = workouts[key]
        exercise_name = _clean(row.get("exercise_title"), 100)

        if not exercise_name:
            omitted += 1
            warnings.append(f"Fila {row_number}: serie sin nombre de ejercicio.")
            continue

        # Filas consecutivas con el mismo ejercicio forman un bloque; si el
        # ejercicio reaparece más tarde en la sesión, es un bloque nuevo.
        exercise = last_exercise.get(key)

        if exercise is None or exercise.name != exercise_name:
            exercise = ExercisePlan(
                name=exercise_name,
                technique_notes=_clean(row.get("exercise_notes"), 1000) or None,
            )
            workout.exercises.append(exercise)
            last_exercise[key] = exercise

        reps = _number(row.get("reps"))

        if reps is None or reps < 1:
            omitted += 1
            warnings.append(
                f"«{exercise_name}» ({workout.name}, {workout.date}): serie sin "
                "repeticiones (cardio u otra medida), omitida."
            )
            continue

        weight = _number(row.get("weight_kg"))

        if weight is None and row.get("weight_lbs") not in (None, ""):
            pounds = _number(row.get("weight_lbs"))
            weight = None if pounds is None else pounds * LBS_TO_KG

        weight = 0.0 if weight is None else weight

        if weight < 0:
            omitted += 1
            warnings.append(
                f"«{exercise_name}» ({workout.name}, {workout.date}): peso "
                "negativo, serie omitida."
            )
            continue

        raw_type = (row.get("set_type") or "").strip().lower()
        rpe = _number(row.get("rpe"))
        rir = None if rpe is None or not -3 <= 10 - rpe <= 10 else round(10 - rpe, 1)

        exercise.sets.append(
            SetPlan(
                set_type=SET_TYPES.get(raw_type, "working"),
                repetitions=int(reps),
                weight_kg=round(weight, 3),
                rir=rir,
                notes="Al fallo" if raw_type == "failure" else None,
            )
        )

    plans = []

    for workout in workouts.values():
        workout.exercises = [e for e in workout.exercises if e.sets]

        if workout.exercises:
            plans.append(workout)
        else:
            warnings.append(
                f"«{workout.name}» ({workout.date}) no tiene series válidas: omitida."
            )

    return ParsedImport(workouts=plans, omitted_sets=omitted, warnings=warnings)


def import_hevy_workouts(
    connection: Connection,
    user_id: int,
    content: bytes,
    *,
    dry_run: bool,
) -> dict:
    """Interpreta el CSV y, si `dry_run` es falso, lo guarda en la transacción
    de `connection` (quien llama revierte si hay una excepción)."""
    parsed = parse_hevy_csv(content)
    existing: set[tuple[str, str]] = set()

    if parsed.workouts:
        dates = [workout.date for workout in parsed.workouts]
        rows = connection.execute(
            "SELECT date, name FROM workout_sessions "
            "WHERE user_id = ? AND date >= ? AND date <= ?",
            (user_id, min(dates), max(dates)),
        ).fetchall()
        existing = {(row["date"], row["name"].strip().lower()) for row in rows}

    new_sessions = skipped = exercises = sets = 0
    pending: list[WorkoutPlan] = []

    for workout in parsed.workouts:
        if (workout.date, workout.name.strip().lower()) in existing:
            skipped += 1
            continue

        pending.append(workout)
        new_sessions += 1
        exercises += len(workout.exercises)
        sets += sum(len(exercise.sets) for exercise in workout.exercises)

    if not dry_run:
        for workout in pending:
            session_id = connection.execute(
                "INSERT INTO workout_sessions (user_id, date, name, notes) "
                "VALUES (?, ?, ?, ?)",
                (user_id, workout.date, workout.name, workout.notes),
            ).lastrowid

            for position, exercise in enumerate(workout.exercises, start=1):
                exercise_id = connection.execute(
                    "INSERT INTO workout_exercises (workout_session_id, name, "
                    "muscle_group, position, technique_notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        session_id, exercise.name, UNCLASSIFIED_MUSCLE_GROUP,
                        position, exercise.technique_notes,
                    ),
                ).lastrowid

                for set_position, item in enumerate(exercise.sets, start=1):
                    connection.execute(
                        "INSERT INTO workout_sets (workout_exercise_id, "
                        "set_type, position, repetitions, weight_kg, rir, "
                        "notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            exercise_id, item.set_type, set_position,
                            item.repetitions, item.weight_kg, item.rir,
                            item.notes,
                        ),
                    )

    shown = parsed.warnings[:MAX_WARNINGS_SHOWN]
    hidden = len(parsed.warnings) - len(shown)

    if hidden > 0:
        shown.append(f"… y {hidden} avisos más.")

    return {
        "dry_run": dry_run,
        "sessions": new_sessions,
        "skipped_sessions": skipped,
        "exercises": exercises,
        "sets": sets,
        "omitted_sets": parsed.omitted_sets,
        "warnings": shown,
    }
