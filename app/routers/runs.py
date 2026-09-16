import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.dependencies import get_current_user
from app.db import get_connection
from app.schemas import RunCreate, RunResponse, RunUpdate,UserResponse


router = APIRouter(
    prefix="/runs",
    tags=["runs"],
)


def calculate_average_pace(
    distance_km: float,
    duration_seconds: int,
) -> float:
    return round(duration_seconds / distance_km, 2)


def row_to_run(row: sqlite3.Row) -> RunResponse:
    return RunResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        distance_km=row["distance_km"],
        duration_seconds=row["duration_seconds"],
        average_pace_seconds_km=row["average_pace_seconds_km"],
        notes=row["notes"],
    )


@router.post(
    "/",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_run(
    run: RunCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> RunResponse:
    average_pace_seconds_km = calculate_average_pace(
        distance_km=run.distance_km,
        duration_seconds=run.duration_seconds,
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO runs (
                user_id,
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                run.date.isoformat(),
                run.distance_km,
                run.duration_seconds,
                average_pace_seconds_km,
                run.notes,
            ),
        )

        row = connection.execute(
            """
            SELECT
                id,
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            FROM runs
            WHERE id = ? AND user_id = ?
            """,
            (cursor.lastrowid, current_user.id),
        ).fetchone()

    return row_to_run(row)
@router.get("/", response_model=list[RunResponse])
def list_runs(current_user: UserResponse = Depends(get_current_user)) -> list[RunResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            FROM runs
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (current_user.id,)
        ).fetchall()

    return [row_to_run(row) for row in rows]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: int, current_user: UserResponse = Depends(get_current_user)) -> RunResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            FROM runs
            WHERE id = ? AND user_id = ?
            """,
            (run_id, current_user.id),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una carrera con ese id.",
        )

    return row_to_run(row)


@router.put(
    "/{run_id}",
    response_model=RunResponse,
)
def update_run(
    run_id: int,
    run: RunUpdate,
    current_user: UserResponse = Depends(get_current_user)
) -> RunResponse:
    average_pace_seconds_km = calculate_average_pace(
        distance_km=run.distance_km,
        duration_seconds=run.duration_seconds,
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE runs
            SET
                date = ?,
                distance_km = ?,
                duration_seconds = ?,
                average_pace_seconds_km = ?,
                notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                run.date.isoformat(),
                run.distance_km,
                run.duration_seconds,
                average_pace_seconds_km,
                run.notes,
                run_id,
                current_user.id,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una carrera con ese id.",
            )

        row = connection.execute(
            """
            SELECT
                id,
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            FROM runs
            WHERE id = ? AND user_id = ?
            """,
            (run_id,current_user.id),
        ).fetchone()

    return row_to_run(row)


@router.delete(
    "/{run_id}",
    response_model=None,
)
def delete_run(run_id: int, current_user: UserResponse = Depends(get_current_user)) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM runs
            WHERE id = ? AND user_id = ?
            """,
            (run_id, current_user.id),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una carrera con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)