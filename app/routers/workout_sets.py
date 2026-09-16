import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    UserResponse,
    WorkoutSetCreate,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)


router = APIRouter(
    tags=["workout sets"],
)


WORKOUT_SET_SELECT_COLUMNS = """
    workout_set.id,
    workout_set.workout_exercise_id,
    workout_set.set_type,
    workout_set.position,
    workout_set.target_rep_range,
    workout_set.repetitions,
    workout_set.weight_kg,
    workout_set.rir,
    workout_set.notes
"""


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


def ensure_owned_exercise_exists(
    connection: sqlite3.Connection,
    *,
    exercise_id: int,
    user_id: int,
) -> None:
    exercise = connection.execute(
        """
        SELECT exercise.id
        FROM workout_exercises AS exercise
        JOIN workout_sessions AS session
            ON session.id = exercise.workout_session_id
        WHERE exercise.id = ?
          AND session.user_id = ?
        """,
        (exercise_id, user_id),
    ).fetchone()

    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio con ese id.",
        )


def get_owned_set_row(
    connection: sqlite3.Connection,
    *,
    set_id: int,
    user_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        f"""
        SELECT {WORKOUT_SET_SELECT_COLUMNS}
        FROM workout_sets AS workout_set
        JOIN workout_exercises AS exercise
            ON exercise.id = workout_set.workout_exercise_id
        JOIN workout_sessions AS session
            ON session.id = exercise.workout_session_id
        WHERE workout_set.id = ?
          AND session.user_id = ?
        """,
        (set_id, user_id),
    ).fetchone()


@router.post(
    "/workout-exercises/{exercise_id}/sets/",
    response_model=WorkoutSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_set(
    exercise_id: int,
    workout_set: WorkoutSetCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutSetResponse:
    try:
        with get_connection() as connection:
            ensure_owned_exercise_exists(
                connection,
                exercise_id=exercise_id,
                user_id=current_user.id,
            )

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

            row = get_owned_set_row(
                connection,
                set_id=cursor.lastrowid,
                user_id=current_user.id,
            )
    except sqlite3.IntegrityError as error:
        error_message = str(error)

        if (
            "workout_sets.workout_exercise_id, workout_sets.position"
            in error_message
        ):
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
def list_workout_sets(
    exercise_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> list[WorkoutSetResponse]:
    with get_connection() as connection:
        ensure_owned_exercise_exists(
            connection,
            exercise_id=exercise_id,
            user_id=current_user.id,
        )

        rows = connection.execute(
            f"""
            SELECT {WORKOUT_SET_SELECT_COLUMNS}
            FROM workout_sets AS workout_set
            JOIN workout_exercises AS exercise
                ON exercise.id = workout_set.workout_exercise_id
            JOIN workout_sessions AS session
                ON session.id = exercise.workout_session_id
            WHERE workout_set.workout_exercise_id = ?
              AND session.user_id = ?
            ORDER BY workout_set.position ASC
            """,
            (exercise_id, current_user.id),
        ).fetchall()

    return [row_to_workout_set(row) for row in rows]


@router.get(
    "/workout-sets/{set_id}",
    response_model=WorkoutSetResponse,
)
def get_workout_set(
    set_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutSetResponse:
    with get_connection() as connection:
        row = get_owned_set_row(
            connection,
            set_id=set_id,
            user_id=current_user.id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una serie con ese id.",
        )

    return row_to_workout_set(row)


@router.put(
    "/workout-sets/{set_id}",
    response_model=WorkoutSetResponse,
)
def update_workout_set(
    set_id: int,
    workout_set: WorkoutSetUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutSetResponse:
    try:
        with get_connection() as connection:
            owned_row = get_owned_set_row(
                connection,
                set_id=set_id,
                user_id=current_user.id,
            )

            if owned_row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe una serie con ese id.",
                )

            cursor = connection.execute(
                """
                UPDATE workout_sets
                SET
                    set_type = ?,
                    position = ?,
                    target_rep_range = ?,
                    repetitions = ?,
                    weight_kg = ?,
                    rir = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    workout_set.set_type,
                    workout_set.position,
                    workout_set.target_rep_range,
                    workout_set.repetitions,
                    workout_set.weight_kg,
                    workout_set.rir,
                    workout_set.notes,
                    set_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe una serie con ese id.",
                )

            row = get_owned_set_row(
                connection,
                set_id=set_id,
                user_id=current_user.id,
            )
    except sqlite3.IntegrityError as error:
        error_message = str(error)

        if (
            "workout_sets.workout_exercise_id, workout_sets.position"
            in error_message
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una serie en esa posición para este ejercicio.",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No se pudo actualizar la serie: {error_message}",
        ) from error

    return row_to_workout_set(row)


@router.delete(
    "/workout-sets/{set_id}",
    response_model=None,
)
def delete_workout_set(
    set_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        owned_row = get_owned_set_row(
            connection,
            set_id=set_id,
            user_id=current_user.id,
        )

        if owned_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una serie con ese id.",
            )

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