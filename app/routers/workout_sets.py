import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import WorkoutSetCreate, WorkoutSetResponse


router = APIRouter(
    tags=["workout sets"],
)


def row_to_workout_set(row: sqlite3.Row) -> WorkoutSetResponse:
    return WorkoutSetResponse(
        id=row["id"],
        workout_exercise_id=row["workout_exercise_id"],
        set_type=row["set_type"],
        position=row["position"],
        target_rep_range=row["target_rep_range"],
        repetitions=row["repetitions"],
        weight_kg=row["weight_kg"],
        rir=row["rir"],
        notes=row["notes"],
        volume_kg=row["repetitions"] * row["weight_kg"],
    )


def ensure_exercise_exists(exercise_id: int) -> None:
    with get_connection() as connection:
        exercise = connection.execute(
            "SELECT id FROM workout_exercises WHERE id = ?",
            (exercise_id,),
        ).fetchone()

    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio con ese id.",
        )


@router.post(
    "/workout-exercises/{exercise_id}/sets/",
    response_model=WorkoutSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_set(
    exercise_id: int,
    workout_set: WorkoutSetCreate,
) -> WorkoutSetResponse:
    ensure_exercise_exists(exercise_id)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO workout_sets (
                    workout_exercise_id,
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exercise_id,
                    workout_set.set_type,
                    workout_set.position,
                    workout_set.target_rep_range,
                    workout_set.repetitions,
                    workout_set.weight_kg,
                    workout_set.rir,
                    workout_set.notes,
                ),
            )

            row = connection.execute(
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
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

    except sqlite3.IntegrityError as error:
        error_message = str(error)

        if "workout_sets.workout_exercise_id, workout_sets.position" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una serie en esa posición para este ejercicio.",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No se pudo guardar la serie: {error_message}",
        ) from error
    return row_to_workout_set(row)


@router.get(
    "/workout-exercises/{exercise_id}/sets/",
    response_model=list[WorkoutSetResponse],
)
def list_workout_sets(exercise_id: int) -> list[WorkoutSetResponse]:
    ensure_exercise_exists(exercise_id)

    with get_connection() as connection:
        rows = connection.execute(
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
            WHERE workout_exercise_id = ?
            ORDER BY position ASC
            """,
            (exercise_id,),
        ).fetchall()

    return [row_to_workout_set(row) for row in rows]


@router.get(
    "/workout-sets/{set_id}",
    response_model=WorkoutSetResponse,
)
def get_workout_set(set_id: int) -> WorkoutSetResponse:
    with get_connection() as connection:
        row = connection.execute(
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
            WHERE id = ?
            """,
            (set_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una serie con ese id.",
        )

    return row_to_workout_set(row)


@router.delete(
    "/workout-sets/{set_id}",
    response_model=None,
)
def delete_workout_set(set_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_sets
            WHERE id = ?
            """,
            (set_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una serie con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)



