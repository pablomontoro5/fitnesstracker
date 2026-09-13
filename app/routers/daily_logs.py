import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_current_user
from app.schemas import (
    DailyLogCreate,
    DailyLogResponse,
    DailyLogUpdate,
    UserResponse,
)

from app.db import get_connection

router = APIRouter(
    prefix="/daily-logs",
    tags=["daily logs"],
)


def row_to_daily_log(row: sqlite3.Row) -> DailyLogResponse:
    return DailyLogResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        steps=row["steps"],
        notes=row["notes"],
    )


@router.post(
    "/",
    response_model=DailyLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_daily_log(
    daily_log: DailyLogCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> DailyLogResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO daily_logs (user_id, date, steps, notes)
                VALUES (?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    daily_log.date.isoformat(),
                    daily_log.steps,
                    daily_log.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT id, date, steps, notes
                FROM daily_logs
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro para esta fecha.",
        ) from error

    return row_to_daily_log(row)


@router.get("/", response_model=list[DailyLogResponse])
def list_daily_logs(
    current_user: UserResponse = Depends(get_current_user),
) -> list[DailyLogResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, date, steps, notes
            FROM daily_logs
            WHERE user_id = ?
            ORDER BY date DESC
            """,
            (current_user.id,),
        ).fetchall()

    return [row_to_daily_log(row) for row in rows]

@router.get("/{log_date}", response_model=DailyLogResponse)
def get_daily_log(
    log_date: date,
    current_user: UserResponse = Depends(get_current_user),
) -> DailyLogResponse:

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, date, steps, notes
            FROM daily_logs
            WHERE date = ? AND user_id = ?
            """,
            (log_date.isoformat(), current_user.id),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro para esta fecha.",
        )

    return row_to_daily_log(row)


@router.put("/{log_date}", response_model=DailyLogResponse)
def update_daily_log(
    log_date: date,
    daily_log: DailyLogUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> DailyLogResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE daily_logs
            SET steps = ?, notes = ?
            WHERE date = ? AND user_id = ?
            """,
            (
                daily_log.steps,
                daily_log.notes,
                log_date.isoformat(),
                current_user.id,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un registro para esta fecha.",
            )

        row = connection.execute(
            """
            SELECT id, date, steps, notes
            FROM daily_logs
            WHERE date = ? AND user_id = ?
            """,
            (log_date.isoformat(), current_user.id),
        ).fetchone()

    return row_to_daily_log(row)


@router.delete(
    "/{log_date}",
    response_model=None,
)
def delete_daily_log(
    log_date: date,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM daily_logs
            WHERE date = ? AND user_id = ?
            """,
            (log_date.isoformat(), current_user.id),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro para esta fecha.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)