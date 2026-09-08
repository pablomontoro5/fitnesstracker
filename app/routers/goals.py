import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import (
    FitnessGoalProgressResponse,
    FitnessGoalResponse,
    FitnessGoalUpsert,
    GoalType,
)


router = APIRouter(
    prefix="/goals",
    tags=["goals"],
)


def row_to_fitness_goal(row: sqlite3.Row) -> FitnessGoalResponse:
    return FitnessGoalResponse(
        id=row["id"],
        goal_type=row["goal_type"],
        target_value=row["target_value"],
    )


def get_current_value(
    connection: sqlite3.Connection,
    goal_type: GoalType,
    today: date,
) -> float:
    week_start = today - timedelta(days=today.weekday())

    if goal_type == "daily_steps":
        row = connection.execute(
            """
            SELECT COALESCE(steps, 0) AS current_value
            FROM daily_logs
            WHERE date = ?
            """,
            (today.isoformat(),),
        ).fetchone()

        return float(row["current_value"]) if row else 0.0

    if goal_type == "weekly_workouts":
        row = connection.execute(
            """
            SELECT COUNT(*) AS current_value
            FROM workout_sessions
            WHERE date BETWEEN ? AND ?
            """,
            (week_start.isoformat(), today.isoformat()),
        ).fetchone()

        return float(row["current_value"])

    row = connection.execute(
        """
        SELECT COALESCE(SUM(distance_km), 0) AS current_value
        FROM runs
        WHERE date BETWEEN ? AND ?
        """,
        (week_start.isoformat(), today.isoformat()),
    ).fetchone()

    return float(row["current_value"])


@router.put(
    "/{goal_type}",
    response_model=FitnessGoalResponse,
)
def create_or_update_goal(
    goal_type: GoalType,
    goal: FitnessGoalUpsert,
) -> FitnessGoalResponse:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO fitness_goals (
                goal_type,
                target_value,
                updated_at
            )
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(goal_type) DO UPDATE SET
                target_value = excluded.target_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (goal_type, goal.target_value),
        )

        row = connection.execute(
            """
            SELECT id, goal_type, target_value
            FROM fitness_goals
            WHERE goal_type = ?
            """,
            (goal_type,),
        ).fetchone()

    return row_to_fitness_goal(row)


@router.get(
    "/",
    response_model=list[FitnessGoalResponse],
)
def list_goals() -> list[FitnessGoalResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, goal_type, target_value
            FROM fitness_goals
            ORDER BY goal_type ASC
            """
        ).fetchall()

    return [row_to_fitness_goal(row) for row in rows]

def build_goals_progress(
    today: date,
) -> list[FitnessGoalProgressResponse]:
    progress_items: list[FitnessGoalProgressResponse] = []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT goal_type, target_value
            FROM fitness_goals
            ORDER BY goal_type ASC
            """
        ).fetchall()

        for row in rows:
            current_value = get_current_value(
                connection=connection,
                goal_type=row["goal_type"],
                today=today,
            )
            target_value = float(row["target_value"])

            progress_items.append(
                FitnessGoalProgressResponse(
                    goal_type=row["goal_type"],
                    target_value=target_value,
                    current_value=current_value,
                    progress_percentage=round(
                        min((current_value / target_value) * 100, 100),
                        1,
                    ),
                    is_completed=current_value >= target_value,
                )
            )

    return progress_items

@router.get(
    "/progress",
    response_model=list[FitnessGoalProgressResponse],
)
def get_goals_progress() -> list[FitnessGoalProgressResponse]:
    return build_goals_progress(today=date.today())
@router.delete(
    "/{goal_type}",
    response_model=None,
)
def delete_goal(goal_type: GoalType) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM fitness_goals
            WHERE goal_type = ?
            """,
            (goal_type,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un objetivo de este tipo.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)