import sqlite3
from datetime import date

from fastapi import APIRouter, HTTPException, Response,status

from app.db import get_connection
from app.schemas import WorkoutSessionCreate, WorkoutSessionResponse, WorkoutSessionUpdate

router = APIRouter(
    prefix="/workout-sessions",
    tags=["workout sessions"],
)


def row_to_workout_session(row: sqlite3.Row) -> WorkoutSessionResponse:
    return WorkoutSessionResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        name=row["name"],
        notes=row["notes"],
    )


@router.post(
    "/",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_session(
    workout_session: WorkoutSessionCreate,
) -> WorkoutSessionResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO workout_sessions (date, name, notes)
            VALUES (?, ?, ?)
            """,
            (
                workout_session.date.isoformat(),
                workout_session.name.strip(),
                workout_session.notes,
            ),
        )

        row = connection.execute(
            """
            SELECT id, date, name, notes
            FROM workout_sessions
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return row_to_workout_session(row)


@router.get("/", response_model=list[WorkoutSessionResponse])
def list_workout_sessions() -> list[WorkoutSessionResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, date, name, notes
            FROM workout_sessions
            ORDER BY date DESC, id DESC
            """
        ).fetchall()

    return [row_to_workout_session(row) for row in rows]

@router.post(
    "/{session_id}/repeat",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def repeat_workout_session(session_id: int) -> WorkoutSessionResponse:
    with get_connection() as connection:
        original_session = connection.execute(
            """
            SELECT id, name, notes
            FROM workout_sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

        if original_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una sesión con ese id.",
            )

        new_session_cursor = connection.execute(
            """
            INSERT INTO workout_sessions (date, name, notes)
            VALUES (?, ?, ?)
            """,
            (
                date.today().isoformat(),
                original_session["name"],
                original_session["notes"],
            ),
        )

        new_session_id = new_session_cursor.lastrowid

        original_exercises = connection.execute(
            """
            SELECT name, muscle_group, position, technique_notes
            FROM workout_exercises
            WHERE workout_session_id = ?
            ORDER BY position ASC
            """,
            (session_id,),
        ).fetchall()

        connection.executemany(
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
            [
                (
                    new_session_id,
                    exercise["name"],
                    exercise["muscle_group"],
                    exercise["position"],
                    exercise["technique_notes"],
                )
                for exercise in original_exercises
            ],
        )

        row = connection.execute(
            """
            SELECT id, date, name, notes
            FROM workout_sessions
            WHERE id = ?
            """,
            (new_session_id,),
        ).fetchone()

    return row_to_workout_session(row)

@router.get("/{session_id}", response_model=WorkoutSessionResponse)
def get_workout_session(session_id: int) -> WorkoutSessionResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, date, name, notes
            FROM workout_sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una sesión con ese id.",
        )

    return row_to_workout_session(row)


@router.put(
    "/{session_id}",
    response_model=WorkoutSessionResponse,
)
def update_workout_session(
    session_id: int,
    workout_session: WorkoutSessionUpdate,
) -> WorkoutSessionResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE workout_sessions
            SET date = ?, name = ?, notes = ?
            WHERE id = ?
            """,
            (
                workout_session.date.isoformat(),
                workout_session.name.strip(),
                workout_session.notes,
                session_id,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una sesión con ese id.",
            )

        row = connection.execute(
            """
            SELECT id, date, name, notes
            FROM workout_sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

    return row_to_workout_session(row)


@router.put(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workout_session(session_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_sessions
            WHERE id = ?
            """,
            (session_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una sesión con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)