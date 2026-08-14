import sqlite3
from collections import defaultdict

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
    "/progress",
    response_model=WorkoutProgressResponse,
)
def get_workout_progress(
    exercise_name: str = Query(min_length=1, max_length=120),
) -> WorkoutProgressResponse:
    normalized_exercise_name = exercise_name.strip()

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
            "total_volume_kg": 0.0,
            "sets": [],
        }
    )

    for row in rows:
        session = sessions[row["session_id"]]

        session["session_id"] = row["session_id"]
        session["session_name"] = row["session_name"]
        session["date"] = row["session_date"]
        session["total_volume_kg"] += row["volume_kg"]
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
                date=session["date"],
                total_volume_kg=session["total_volume_kg"],
                sets=session["sets"],
            )
            for session in sessions.values()
        ],
    )