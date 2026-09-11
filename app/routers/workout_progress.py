from collections import defaultdict
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.db import get_connection
from app.schemas import (
    WorkoutPersonalRecord,
    WorkoutPersonalRecordsExerciseResponse,
    WorkoutProgressResponse,
    WorkoutProgressSessionResponse,
    WorkoutProgressSetResponse,
)


router = APIRouter(
    prefix="/workouts",
    tags=["workout progress"],
)

@router.get(
    "/exercise-names",
    response_model=list[str],
)
def list_exercise_names_with_progress() -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT workout_exercises.name
            FROM workout_exercises
            INNER JOIN workout_sets
                ON workout_sets.workout_exercise_id = workout_exercises.id
            WHERE workout_sets.set_type = 'working'
            ORDER BY workout_exercises.name COLLATE NOCASE ASC
            """
        ).fetchall()

    return [row["name"] for row in rows]


@router.get(
    "/progress",
    response_model=WorkoutProgressResponse,
)
def get_workout_progress(
    exercise_name: str = Query(min_length=1, max_length=120),
) -> WorkoutProgressResponse:
    normalized_exercise_name = exercise_name.strip()

    if not normalized_exercise_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre del ejercicio no puede estar vacío.",
        )

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                workout_sessions.id AS session_id,
                workout_sessions.date AS session_date,
                workout_sessions.name AS session_name,
                workout_sets.id AS set_id,
                workout_sets.position AS set_position,
                workout_sets.repetitions,
                workout_sets.weight_kg,
                workout_sets.rir,
                workout_sets.repetitions * workout_sets.weight_kg AS volume_kg
            FROM workout_sets
            INNER JOIN workout_exercises
                ON workout_sets.workout_exercise_id = workout_exercises.id
            INNER JOIN workout_sessions
                ON workout_exercises.workout_session_id = workout_sessions.id
            WHERE workout_exercises.name = ?
                AND workout_sets.set_type = 'working'
            ORDER BY
                workout_sessions.date ASC,
                workout_sessions.id ASC,
                workout_sets.position ASC
            """,
            (normalized_exercise_name,),
        ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No existen series de trabajo para ese ejercicio."
            ),
        )

    sessions: dict[int, dict] = defaultdict(
        lambda: {
            "session_id": 0,
            "session_name": "",
            "date": "",
            "working_sets": 0,
            "total_repetitions": 0,
            "total_volume_kg": 0.0,
            "max_weight_kg": 0.0,
            "max_volume_set_kg": 0.0,
            "sets": [],
        }
    )

    for row in rows:
        session = sessions[row["session_id"]]

        session["session_id"] = row["session_id"]
        session["session_name"] = row["session_name"]
        session["date"] = row["session_date"]
        session["total_volume_kg"] += row["volume_kg"]
        session["working_sets"] += 1
        session["total_repetitions"] += row["repetitions"]
        session["max_weight_kg"] = max(
            session["max_weight_kg"],
            row["weight_kg"],
        )
        session["max_volume_set_kg"] = max(
            session["max_volume_set_kg"],
            row["volume_kg"],
        )
        session["sets"].append(
            WorkoutProgressSetResponse(
                id=row["set_id"],
                position=row["set_position"],
                repetitions=row["repetitions"],
                weight_kg=row["weight_kg"],
                rir=row["rir"],
                volume_kg=row["volume_kg"],
            )
        )

    return WorkoutProgressResponse(
        exercise_name=normalized_exercise_name,
        sessions=[
            WorkoutProgressSessionResponse(
                session_id=session["session_id"],
                session_name=session["session_name"],
                date=date.fromisoformat(session["date"]),
                working_sets=session["working_sets"],
                total_repetitions=session["total_repetitions"],
                total_volume_kg=round(session["total_volume_kg"], 2),
                max_weight_kg=round(session["max_weight_kg"], 2),
                max_volume_set_kg=round(
                    session["max_volume_set_kg"],
                    2,
                ),
                sets=session["sets"],
            )
            for session in sessions.values()
        ],
    )

PERSONAL_RECORDS_SELECT = """
    SELECT
        workout_exercises.name AS exercise_name,
        workout_sessions.id AS session_id,
        workout_sessions.name AS session_name,
        workout_sessions.date AS session_date,
        workout_sets.id AS set_id,
        workout_sets.position AS set_position,
        workout_sets.repetitions,
        workout_sets.weight_kg,
        workout_sets.repetitions * workout_sets.weight_kg AS volume_kg,
        workout_sets.weight_kg * (
            1 + workout_sets.repetitions / 30.0
        ) AS estimated_one_rep_max_kg
    FROM workout_sets
    INNER JOIN workout_exercises
        ON workout_sets.workout_exercise_id = workout_exercises.id
    INNER JOIN workout_sessions
        ON workout_exercises.workout_session_id = workout_sessions.id
    WHERE workout_sets.set_type = 'working'
"""


def row_to_personal_record(
    row: dict,
    *,
    metric: str,
    label: str,
    value: float,
    unit: str,
    set_id: int | None,
    repetitions: int | None,
    weight_kg: float | None,
    volume_kg: float | None,
) -> WorkoutPersonalRecord:
    return WorkoutPersonalRecord(
        metric=metric,
        label=label,
        value=round(value, 2),
        unit=unit,
        date=date.fromisoformat(row["session_date"]),
        session_id=row["session_id"],
        session_name=row["session_name"],
        set_id=set_id,
        repetitions=repetitions,
        weight_kg=weight_kg,
        volume_kg=volume_kg,
    )


def get_first_record_by_highest_value(
    rows: list,
    value_key: str,
):
    return max(
        rows,
        key=lambda row: (
            row[value_key],
            -date.fromisoformat(row["session_date"]).toordinal(),
            -row["session_id"],
            -row["set_position"],
        ),
    )


def build_personal_records(
    exercise_name: str,
    rows: list,
) -> WorkoutPersonalRecordsExerciseResponse:
    max_weight_row = get_first_record_by_highest_value(
        rows,
        "weight_kg",
    )
    max_repetitions_row = get_first_record_by_highest_value(
        rows,
        "repetitions",
    )
    max_set_volume_row = get_first_record_by_highest_value(
        rows,
        "volume_kg",
    )
    estimated_one_rep_max_row = get_first_record_by_highest_value(
        rows,
        "estimated_one_rep_max_kg",
    )

    session_volumes: dict[int, dict] = {}

    for row in rows:
        session_id = row["session_id"]

        if session_id not in session_volumes:
            session_volumes[session_id] = {
                "session_id": row["session_id"],
                "session_name": row["session_name"],
                "session_date": row["session_date"],
                "total_volume_kg": 0.0,
            }

        session_volumes[session_id]["total_volume_kg"] += row["volume_kg"]

    max_session_volume = max(
        session_volumes.values(),
        key=lambda session: (
            session["total_volume_kg"],
            -date.fromisoformat(session["session_date"]).toordinal(),
            -session["session_id"],
        ),
    )

    return WorkoutPersonalRecordsExerciseResponse(
        exercise_name=exercise_name,
        records=[
            row_to_personal_record(
                max_weight_row,
                metric="max_weight_kg",
                label="Carga máxima",
                value=max_weight_row["weight_kg"],
                unit="kg",
                set_id=max_weight_row["set_id"],
                repetitions=max_weight_row["repetitions"],
                weight_kg=max_weight_row["weight_kg"],
                volume_kg=max_weight_row["volume_kg"],
            ),
            row_to_personal_record(
                max_repetitions_row,
                metric="max_repetitions",
                label="Más repeticiones",
                value=max_repetitions_row["repetitions"],
                unit="repeticiones",
                set_id=max_repetitions_row["set_id"],
                repetitions=max_repetitions_row["repetitions"],
                weight_kg=max_repetitions_row["weight_kg"],
                volume_kg=max_repetitions_row["volume_kg"],
            ),
            row_to_personal_record(
                max_set_volume_row,
                metric="max_set_volume_kg",
                label="Mejor volumen de serie",
                value=max_set_volume_row["volume_kg"],
                unit="kg",
                set_id=max_set_volume_row["set_id"],
                repetitions=max_set_volume_row["repetitions"],
                weight_kg=max_set_volume_row["weight_kg"],
                volume_kg=max_set_volume_row["volume_kg"],
            ),
            row_to_personal_record(
                estimated_one_rep_max_row,
                metric="estimated_one_rep_max_kg",
                label="1RM estimado",
                value=estimated_one_rep_max_row["estimated_one_rep_max_kg"],
                unit="kg",
                set_id=estimated_one_rep_max_row["set_id"],
                repetitions=estimated_one_rep_max_row["repetitions"],
                weight_kg=estimated_one_rep_max_row["weight_kg"],
                volume_kg=estimated_one_rep_max_row["volume_kg"],
            ),
            row_to_personal_record(
                max_session_volume,
                metric="max_session_volume_kg",
                label="Mayor volumen de sesión",
                value=max_session_volume["total_volume_kg"],
                unit="kg",
                set_id=None,
                repetitions=None,
                weight_kg=None,
                volume_kg=max_session_volume["total_volume_kg"],
            ),
        ],
    )


@router.get(
    "/personal-records",
    response_model=list[WorkoutPersonalRecordsExerciseResponse],
)
def get_workout_personal_records(
    exercise_name: str | None = Query(
        default=None,
        max_length=120,
    ),
) -> list[WorkoutPersonalRecordsExerciseResponse]:
    normalized_exercise_name = None

    if exercise_name is not None:
        normalized_exercise_name = exercise_name.strip()

        if not normalized_exercise_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El nombre del ejercicio no puede estar vacío.",
            )

    query = PERSONAL_RECORDS_SELECT
    parameters: tuple[str, ...] = ()

    if normalized_exercise_name is not None:
        query += """
            AND workout_exercises.name = ?
        """
        parameters = (normalized_exercise_name,)

    query += """
        ORDER BY
            workout_exercises.name COLLATE NOCASE ASC,
            workout_sessions.date ASC,
            workout_sessions.id ASC,
            workout_sets.position ASC
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    if normalized_exercise_name is not None and not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existen series de trabajo para ese ejercicio.",
        )

    exercises: dict[str, list] = defaultdict(list)

    for row in rows:
        exercises[row["exercise_name"]].append(row)

    return [
        build_personal_records(exercise_name, exercise_rows)
        for exercise_name, exercise_rows in exercises.items()
    ]