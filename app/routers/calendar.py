from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    CalendarActivityDayResponse,
    CalendarActivityResponse,
    CalendarPlannedWorkoutResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
)


MAX_CALENDAR_RANGE_DAYS = 366


@router.get(
    "/activity",
    response_model=CalendarActivityResponse,
)
def get_calendar_activity(
    start_date: date,
    end_date: date,
    current_user: UserResponse = Depends(get_current_user),
) -> CalendarActivityResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    period_days = (end_date - start_date).days + 1
    if period_days > MAX_CALENDAR_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "El intervalo del calendario no puede superar "
                "366 días."
            ),
        )

    start_date_value = start_date.isoformat()
    end_date_value = end_date.isoformat()

    with get_connection() as connection:
        step_rows = connection.execute(
            """
            SELECT
                date,
                steps
            FROM daily_logs
            WHERE user_id = ?
              AND date BETWEEN ? AND ?
            """,
            (
                current_user.id,
                start_date_value,
                end_date_value,
            ),
        ).fetchall()

        recovery_rows = connection.execute(
            """
            SELECT
                date,
                sleep_minutes,
                is_rest_day
            FROM daily_recovery_logs
            WHERE user_id = ?
              AND date BETWEEN ? AND ?
            """,
            (
                current_user.id,
                start_date_value,
                end_date_value,
            ),
        ).fetchall()

        workout_rows = connection.execute(
            """
            SELECT
                date,
                COUNT(*) AS workout_sessions
            FROM workout_sessions
            WHERE user_id = ?
              AND date BETWEEN ? AND ?
            GROUP BY date
            """,
            (
                current_user.id,
                start_date_value,
                end_date_value,
            ),
        ).fetchall()

        running_rows = connection.execute(
            """
            SELECT
                date,
                SUM(distance_km) AS running_distance_km
            FROM runs
            WHERE user_id = ?
              AND date BETWEEN ? AND ?
            GROUP BY date
            """,
            (
                current_user.id,
                start_date_value,
                end_date_value,
            ),
        ).fetchall()

        planned_rows = connection.execute(
            """
            SELECT
                id,
                scheduled_date,
                name,
                status
            FROM planned_workouts
            WHERE user_id = ?
              AND scheduled_date BETWEEN ? AND ?
            ORDER BY scheduled_date ASC, id ASC
            """,
            (
                current_user.id,
                start_date_value,
                end_date_value,
            ),
        ).fetchall()

    steps_by_date = {
        row["date"]: row["steps"]
        for row in step_rows
    }
    recovery_by_date = {
        row["date"]: row
        for row in recovery_rows
    }
    workouts_by_date = {
        row["date"]: row["workout_sessions"]
        for row in workout_rows
    }
    running_by_date = {
        row["date"]: row["running_distance_km"]
        for row in running_rows
    }

    planned_by_date: dict[str, list[CalendarPlannedWorkoutResponse]] = (
        defaultdict(list)
    )
    for row in planned_rows:
        planned_by_date[row["scheduled_date"]].append(
            CalendarPlannedWorkoutResponse(
                id=row["id"],
                name=row["name"],
                status=row["status"],
            )
        )

    days: list[CalendarActivityDayResponse] = []
    current_date = start_date

    while current_date <= end_date:
        current_date_value = current_date.isoformat()
        recovery = recovery_by_date.get(current_date_value)
        workout_sessions = workouts_by_date.get(current_date_value, 0)

        days.append(
            CalendarActivityDayResponse(
                date=current_date,
                steps=steps_by_date.get(current_date_value, 0),
                has_workout=workout_sessions > 0,
                workout_sessions=workout_sessions,
                running_distance_km=float(
                    running_by_date.get(current_date_value, 0.0)
                ),
                sleep_minutes=(
                    recovery["sleep_minutes"]
                    if recovery is not None
                    else None
                ),
                is_rest_day=(
                    bool(recovery["is_rest_day"])
                    if recovery is not None
                    else False
                ),
                planned_workouts=planned_by_date[current_date_value],
            )
        )

        current_date += timedelta(days=1)

    return CalendarActivityResponse(
        start_date=start_date,
        end_date=end_date,
        days=days,
    )