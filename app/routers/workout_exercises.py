import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    UserResponse,
    WorkoutExerciseCreate,
    WorkoutExerciseResponse,
    WorkoutExerciseUpdate,
)


router = APIRouter(
    tags=["workout exercises"],
)


WORKOUT_EXERCISE_SELECT_COLUMNS = """
    exercise.id,
    exercise.workout_session_id,
    exercise.name,
    exercise.muscle_group,
    exercise.position,
    exercise.technique_notes
"""


def row_to_workout_exercise(row: sqlite3.Row) -> WorkoutExerciseResponse:
    return WorkoutExerciseResponse(
        id=row["id"],
        workout_session_id=row["workout_session_id"],
        name=row["name"],
        muscle_group=row["muscle_group"],
        position=row["position"],
        technique_notes=row["technique_notes"],
    )


def ensure_owned_session_exists(
    connection: sqlite3.Connection,
    *,
    session_id: int,
    user_id: int,
) -> None:
    session = connection.execute(
        """
        SELECT id
        FROM workout_sessions
        WHERE id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una sesión con ese id.",
        )


def get_owned_exercise_row(
    connection: sqlite3.Connection,
    *,
    exercise_id: int,
    user_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        f"""
        SELECT {WORKOUT_EXERCISE_SELECT_COLUMNS}
        FROM workout_exercises AS exercise
        JOIN workout_sessions AS session
            ON session.id = exercise.workout_session_id
        WHERE exercise.id = ?
          AND session.user_id = ?
        """,
        (exercise_id, user_id),
    ).fetchone()


@router.post(
    "/workout-sessions/{session_id}/exercises/",
    response_model=WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_exercise(
    session_id: int,
    workout_exercise: WorkoutExerciseCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutExerciseResponse:
    try:
        with get_connection() as connection:
            ensure_owned_session_exists(
                connection,
                session_id=session_id,
                user_id=current_user.id,
            )

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

            row = get_owned_exercise_row(
                connection,
                exercise_id=cursor.lastrowid,
                user_id=current_user.id,
            )
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
    current_user: UserResponse = Depends(get_current_user),
) -> list[WorkoutExerciseResponse]:
    with get_connection() as connection:
        ensure_owned_session_exists(
            connection,
            session_id=session_id,
            user_id=current_user.id,
        )

        rows = connection.execute(
            f"""
            SELECT {WORKOUT_EXERCISE_SELECT_COLUMNS}
            FROM workout_exercises AS exercise
            JOIN workout_sessions AS session
                ON session.id = exercise.workout_session_id
            WHERE exercise.workout_session_id = ?
              AND session.user_id = ?
            ORDER BY exercise.position ASC
            """,
            (session_id, current_user.id),
        ).fetchall()

    return [row_to_workout_exercise(row) for row in rows]


@router.get(
    "/workout-exercises/{exercise_id}",
    response_model=WorkoutExerciseResponse,
)
def get_workout_exercise(
    exercise_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutExerciseResponse:
    with get_connection() as connection:
        row = get_owned_exercise_row(
            connection,
            exercise_id=exercise_id,
            user_id=current_user.id,
        )

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
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutExerciseResponse:
    try:
        with get_connection() as connection:
            owned_row = get_owned_exercise_row(
                connection,
                exercise_id=exercise_id,
                user_id=current_user.id,
            )

            if owned_row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe un ejercicio con ese id.",
                )

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

            row = get_owned_exercise_row(
                connection,
                exercise_id=exercise_id,
                user_id=current_user.id,
            )
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
def delete_workout_exercise(
    exercise_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        owned_row = get_owned_exercise_row(
            connection,
            exercise_id=exercise_id,
            user_id=current_user.id,
        )

        if owned_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un ejercicio con ese id.",
            )

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