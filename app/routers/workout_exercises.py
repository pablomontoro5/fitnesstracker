import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import WorkoutExerciseCreate, WorkoutExerciseResponse, WorkoutExerciseUpdate

router = APIRouter(
    tags=["workout exercises"],
)


def row_to_workout_exercise(row: sqlite3.Row) -> WorkoutExerciseResponse:
    return WorkoutExerciseResponse(
        id=row["id"],
        workout_session_id=row["workout_session_id"],
        name=row["name"],
        muscle_group=row["muscle_group"],
        position=row["position"],
        technique_notes=row["technique_notes"],
    )


def ensure_session_exists(session_id: int) -> None:
    with get_connection() as connection:
        session = connection.execute(
            "SELECT id FROM workout_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una sesión con ese id.",
        )


@router.post(
    "/workout-sessions/{session_id}/exercises/",
    response_model=WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_exercise(
    session_id: int,
    workout_exercise: WorkoutExerciseCreate,
) -> WorkoutExerciseResponse:
    ensure_session_exists(session_id)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO workout_exercises (
                    workout_session_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    workout_exercise.name.strip(),
                    workout_exercise.muscle_group.strip(),
                    workout_exercise.position,
                    workout_exercise.technique_notes,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    workout_session_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                FROM workout_exercises
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un ejercicio en esa posición para esta sesión.",
        ) from error

    return row_to_workout_exercise(row)


@router.get(
    "/workout-sessions/{session_id}/exercises/",
    response_model=list[WorkoutExerciseResponse],
)
def list_workout_exercises(
    session_id: int,
) -> list[WorkoutExerciseResponse]:
    ensure_session_exists(session_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                workout_session_id,
                name,
                muscle_group,
                position,
                technique_notes
            FROM workout_exercises
            WHERE workout_session_id = ?
            ORDER BY position ASC
            """,
            (session_id,),
        ).fetchall()

    return [row_to_workout_exercise(row) for row in rows]


@router.get(
    "/workout-exercises/{exercise_id}",
    response_model=WorkoutExerciseResponse,
)
def get_workout_exercise(exercise_id: int) -> WorkoutExerciseResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                workout_session_id,
                name,
                muscle_group,
                position,
                technique_notes
            FROM workout_exercises
            WHERE id = ?
            """,
            (exercise_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio con ese id.",
        )

    return row_to_workout_exercise(row)


@router.put(
    "/workout-exercises/{exercise_id}",
    response_model=WorkoutExerciseResponse,
)
def update_workout_exercise(
    exercise_id: int,
    workout_exercise: WorkoutExerciseUpdate,
) -> WorkoutExerciseResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE workout_exercises
                SET
                    name = ?,
                    muscle_group = ?,
                    position = ?,
                    technique_notes = ?
                WHERE id = ?
                """,
                (
                    workout_exercise.name.strip(),
                    workout_exercise.muscle_group.strip(),
                    workout_exercise.position,
                    workout_exercise.technique_notes,
                    exercise_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe un ejercicio con ese id.",
                )

            row = connection.execute(
                """
                SELECT
                    id,
                    workout_session_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                FROM workout_exercises
                WHERE id = ?
                """,
                (exercise_id,),
            ).fetchone()

    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un ejercicio en esa posición para esta sesión.",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No se pudo actualizar el ejercicio: {error}",
        ) from error

    return row_to_workout_exercise(row)


@router.delete(
    "/workout-exercises/{exercise_id}",
    response_model=None,
)
def delete_workout_exercise(exercise_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_exercises
            WHERE id = ?
            """,
            (exercise_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)