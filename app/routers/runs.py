import sqlite3
from datetime import date

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import RunCreate, RunResponse, RunUpdate


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
def create_run(run: RunCreate) -> RunResponse:
    average_pace_seconds_km = calculate_average_pace(
        distance_km=run.distance_km,
        duration_seconds=run.duration_seconds,
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO runs (
                date,
                distance_km,
                duration_seconds,
                average_pace_seconds_km,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
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
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return row_to_run(row)


@router.get("/", response_model=list[RunResponse])
def list_runs() -> list[RunResponse]:
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
            ORDER BY date DESC, id DESC
            """
        ).fetchall()

    return [row_to_run(row) for row in rows]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: int) -> RunResponse:
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
            WHERE id = ?
            """,
            (run_id,),
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
            WHERE id = ?
            """,
            (
                run.date.isoformat(),
                run.distance_km,
                run.duration_seconds,
                average_pace_seconds_km,
                run.notes,
                run_id,
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
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()

    return row_to_run(row)


@router.delete(
    "/{run_id}",
    response_model=None,
)
def delete_run(run_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM runs
            WHERE id = ?
            """,
            (run_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una carrera con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)