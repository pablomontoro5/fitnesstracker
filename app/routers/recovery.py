import sqlite3
from datetime import date

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import (
    RecoveryLogCreate,
    RecoveryLogResponse,
    RecoveryLogUpdate,
)


router = APIRouter(
    prefix="/recovery-logs",
    tags=["recovery logs"],
)


def row_to_recovery_log(row: sqlite3.Row) -> RecoveryLogResponse:
    return RecoveryLogResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        sleep_minutes=row["sleep_minutes"],
        sleep_quality=row["sleep_quality"],
        is_rest_day=bool(row["is_rest_day"]),
        notes=row["notes"],
    )


@router.post(
    "/",
    response_model=RecoveryLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recovery_log(
    recovery_log: RecoveryLogCreate,
) -> RecoveryLogResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO daily_recovery_logs (
                    date,
                    sleep_minutes,
                    sleep_quality,
                    is_rest_day,
                    notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    recovery_log.date.isoformat(),
                    recovery_log.sleep_minutes,
                    recovery_log.sleep_quality,
                    int(recovery_log.is_rest_day),
                    recovery_log.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    date,
                    sleep_minutes,
                    sleep_quality,
                    is_rest_day,
                    notes
                FROM daily_recovery_logs
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        if "daily_recovery_logs.date" in str(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Ya existe un registro de recuperación para esta fecha."
                ),
            ) from error

        raise

    return row_to_recovery_log(row)


@router.get(
    "/",
    response_model=list[RecoveryLogResponse],
)
def list_recovery_logs() -> list[RecoveryLogResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                date,
                sleep_minutes,
                sleep_quality,
                is_rest_day,
                notes
            FROM daily_recovery_logs
            ORDER BY date DESC
            """
        ).fetchall()

    return [row_to_recovery_log(row) for row in rows]


@router.get(
    "/{log_date}",
    response_model=RecoveryLogResponse,
)
def get_recovery_log(log_date: date) -> RecoveryLogResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                date,
                sleep_minutes,
                sleep_quality,
                is_rest_day,
                notes
            FROM daily_recovery_logs
            WHERE date = ?
            """,
            (log_date.isoformat(),),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro de recuperación para esta fecha.",
        )

    return row_to_recovery_log(row)


@router.put(
    "/{log_date}",
    response_model=RecoveryLogResponse,
)
def update_recovery_log(
    log_date: date,
    recovery_log: RecoveryLogUpdate,
) -> RecoveryLogResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE daily_recovery_logs
            SET
                sleep_minutes = ?,
                sleep_quality = ?,
                is_rest_day = ?,
                notes = ?
            WHERE date = ?
            """,
            (
                recovery_log.sleep_minutes,
                recovery_log.sleep_quality,
                int(recovery_log.is_rest_day),
                recovery_log.notes,
                log_date.isoformat(),
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un registro de recuperación para esta fecha.",
            )

        row = connection.execute(
            """
            SELECT
                id,
                date,
                sleep_minutes,
                sleep_quality,
                is_rest_day,
                notes
            FROM daily_recovery_logs
            WHERE date = ?
            """,
            (log_date.isoformat(),),
        ).fetchone()

    return row_to_recovery_log(row)


@router.delete(
    "/{log_date}",
    response_model=None,
)
def delete_recovery_log(log_date: date) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM daily_recovery_logs
            WHERE date = ?
            """,
            (log_date.isoformat(),),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro de recuperación para esta fecha.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)