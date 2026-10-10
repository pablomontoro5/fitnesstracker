"""Lógica común de la importación de entrenamientos desde otras aplicaciones.

Cada origen (Hevy, Strong…) convierte su CSV en filas `RawSet`, una por serie,
y este módulo las agrupa en sesiones y ejercicios, las valida y las guarda.

La importación solo AÑADE datos y es repetible: una sesión con la misma fecha y
el mismo nombre que otra ya existente de la cuenta se omite.
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable

from app.db import Connection


MAX_ROWS = 100_000
MAX_WARNINGS_SHOWN = 10
LBS_TO_KG = 0.45359237
UNCLASSIFIED_MUSCLE_GROUP = "Sin clasificar"
DEFAULT_SESSION_NAME = "Entrenamiento"

MONTHS = {
    name: number
    for number, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"),
        start=1,
    )
}
_NAMED_MONTH_DATE_RE = re.compile(
    r"^\s*(\d{1,2})\s+([A-Za-z]{3})[A-Za-z]*\.?\s+(\d{4})"
)


class InvalidImport(ValueError):
    """El archivo no se puede importar; el mensaje se muestra al usuario."""


@dataclass
class RawSet:
    """Una serie tal como la entrega el origen, ya con campos normalizados."""
    row_number: int
    title: str
    workout_key: str          # distingue dos entrenos con el mismo título
    workout_date: str         # AAAA-MM-DD
    description: str | None
    exercise: str
    exercise_notes: str | None
    kind: str                 # working | warmup | drop_set | failure
    weight_kg: float | None
    reps: float | None
    rpe: float | None


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


def clean(value, limit: int) -> str:
    return (value or "").strip()[:limit]


def parse_number(text) -> float | None:
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
    """Fecha (AAAA-MM-DD) de un texto; admite «18 Oct 2023, 18:03» e ISO."""
    text = (text or "").strip()
    match = _NAMED_MONTH_DATE_RE.match(text)

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


def to_kg(value: float | None, unit: str) -> float | None:
    if value is None:
        return None

    return value * LBS_TO_KG if unit == "lb" else value


def read_csv_rows(content: bytes) -> csv.DictReader:
    """Lector con las cabeceras normalizadas (minúsculas y sin espacios)."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidImport(
            "El archivo debe estar codificado en UTF-8 (el CSV original)."
        ) from error

    first_line = text.splitlines()[0] if text.strip() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    reader.fieldnames = [
        (name or "").strip().lower() for name in (reader.fieldnames or [])
    ]

    return reader


def check_row_limit(row_number: int) -> None:
    if row_number > MAX_ROWS + 1:
        raise InvalidImport(
            f"El archivo tiene demasiadas filas (máximo {MAX_ROWS})."
        )


def plan_workouts(raw_sets: Iterable[RawSet]) -> ParsedImport:
    """Agrupa las series en sesiones y ejercicios y descarta las no válidas."""
    workouts: dict[tuple[str, str], WorkoutPlan] = {}
    last_exercise: dict[tuple[str, str], ExercisePlan] = {}
    omitted = 0
    warnings: list[str] = []

    for raw in raw_sets:
        key = (raw.title, raw.workout_key)

        if key not in workouts:
            workouts[key] = WorkoutPlan(
                date=raw.workout_date, name=raw.title, notes=raw.description,
            )

        workout = workouts[key]

        if not raw.exercise:
            omitted += 1
            warnings.append(f"Fila {raw.row_number}: serie sin nombre de ejercicio.")
            continue

        # Filas consecutivas con el mismo ejercicio forman un bloque; si el
        # ejercicio reaparece más tarde en la sesión, es un bloque nuevo.
        exercise = last_exercise.get(key)

        if exercise is None or exercise.name != raw.exercise:
            exercise = ExercisePlan(
                name=raw.exercise, technique_notes=raw.exercise_notes,
            )
            workout.exercises.append(exercise)
            last_exercise[key] = exercise

        where = f"«{raw.exercise}» ({workout.name}, {workout.date})"

        if raw.reps is None or raw.reps < 1:
            omitted += 1
            warnings.append(
                f"{where}: serie sin repeticiones (cardio u otra medida), omitida."
            )
            continue

        weight = 0.0 if raw.weight_kg is None else raw.weight_kg

        if weight < 0:
            omitted += 1
            warnings.append(f"{where}: peso negativo, serie omitida.")
            continue

        rir = (
            None if raw.rpe is None or not -3 <= 10 - raw.rpe <= 10
            else round(10 - raw.rpe, 1)
        )
        exercise.sets.append(
            SetPlan(
                set_type="working" if raw.kind == "failure" else raw.kind,
                repetitions=int(raw.reps),
                weight_kg=round(weight, 3),
                rir=rir,
                notes="Al fallo" if raw.kind == "failure" else None,
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


def save_import(
    connection: Connection,
    user_id: int,
    parsed: ParsedImport,
    *,
    dry_run: bool,
) -> dict:
    """Guarda lo interpretado (o solo lo cuenta si `dry_run`) en la transacción
    de `connection`; quien llama revierte si hay una excepción."""
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
