from collections import defaultdict
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.db import get_connection
from app.schemas import (
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