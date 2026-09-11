import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import (
    FitnessGoalProgressResponse,
    FitnessGoalResponse,
    FitnessGoalUpsert,
    GoalType,
    NutritionGoalProgressItem,
    NutritionGoalsProgressResponse,
)


router = APIRouter(
    prefix="/goals",
    tags=["goals"],
)

ACTIVITY_GOAL_TYPES = {
    "daily_steps",
    "weekly_workouts",
    "weekly_running_km",
}

RECOVERY_GOAL_TYPES = {
    "daily_sleep_minutes",
    "weekly_rest_days",
}

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

    if goal_type == "weekly_running_km":
        row = connection.execute(
            """
            SELECT COALESCE(SUM(distance_km), 0) AS current_value
            FROM runs
            WHERE date BETWEEN ? AND ?
            """,
            (week_start.isoformat(), today.isoformat()),
        ).fetchone()

        return float(row["current_value"])

    if goal_type == "daily_sleep_minutes":
        row = connection.execute(
            """
            SELECT COALESCE(sleep_minutes, 0) AS current_value
            FROM daily_recovery_logs
            WHERE date = ?
            """,
            (today.isoformat(),),
        ).fetchone()

        return float(row["current_value"]) if row else 0.0

    if goal_type == "weekly_rest_days":
        row = connection.execute(
            """
            SELECT COUNT(*) AS current_value
            FROM daily_recovery_logs
            WHERE date BETWEEN ? AND ?
                AND is_rest_day = 1
            """,
            (week_start.isoformat(), today.isoformat()),
        ).fetchone()

        return float(row["current_value"])

    raise ValueError(f"Tipo de objetivo no compatible: {goal_type}")

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
            WHERE goal_type IN (
                'daily_steps',
                'weekly_workouts',
                'weekly_running_km',
                'daily_sleep_minutes',
                'weekly_rest_days'
            )
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
NUTRITION_GOAL_TYPES = {
    "calories": "daily_calories",
    "protein_g": "daily_protein_g",
    "carbs_g": "daily_carbs_g",
    "fat_g": "daily_fat_g",
}


def get_nutrition_totals(
    connection: sqlite3.Connection,
    target_date: date,
) -> dict[str, float]:
    row = connection.execute(
        """
        SELECT
            COALESCE(SUM(nutrition_foods.calories), 0) AS calories,
            COALESCE(SUM(nutrition_foods.protein_g), 0) AS protein_g,
            COALESCE(SUM(nutrition_foods.carbs_g), 0) AS carbs_g,
            COALESCE(SUM(nutrition_foods.fat_g), 0) AS fat_g
        FROM nutrition_days
        LEFT JOIN nutrition_meals
            ON nutrition_meals.nutrition_day_id = nutrition_days.id
        LEFT JOIN nutrition_foods
            ON nutrition_foods.nutrition_meal_id = nutrition_meals.id
        WHERE nutrition_days.date = ?
        """,
        (target_date.isoformat(),),
    ).fetchone()

    return {
        "calories": float(row["calories"]),
        "protein_g": float(row["protein_g"]),
        "carbs_g": float(row["carbs_g"]),
        "fat_g": float(row["fat_g"]),
    }


def build_nutrition_goal_progress_item(
    current_value: float,
    target_value: float | None,
) -> NutritionGoalProgressItem:
    if target_value is None:
        return NutritionGoalProgressItem(
            current_value=round(current_value, 2),
            target_value=None,
            remaining_value=None,
            progress_percentage=None,
            is_completed=False,
        )

    remaining_value = round(target_value - current_value, 2)
    progress_percentage = round(
        (current_value / target_value) * 100,
        1,
    )

    return NutritionGoalProgressItem(
        current_value=round(current_value, 2),
        target_value=round(target_value, 2),
        remaining_value=remaining_value,
        progress_percentage=progress_percentage,
        is_completed=current_value >= target_value,
    )


def build_nutrition_goals_progress(
    target_date: date,
) -> NutritionGoalsProgressResponse:
    with get_connection() as connection:
        totals = get_nutrition_totals(connection, target_date)

        rows = connection.execute(
            """
            SELECT goal_type, target_value
            FROM fitness_goals
            WHERE goal_type IN (
                'daily_calories',
                'daily_protein_g',
                'daily_carbs_g',
                'daily_fat_g'
            )
            """
        ).fetchall()

    goals_by_type = {
        row["goal_type"]: float(row["target_value"])
        for row in rows
    }

    return NutritionGoalsProgressResponse(
        date=target_date,
        calories=build_nutrition_goal_progress_item(
            current_value=totals["calories"],
            target_value=goals_by_type.get(
                NUTRITION_GOAL_TYPES["calories"]
            ),
        ),
        protein_g=build_nutrition_goal_progress_item(
            current_value=totals["protein_g"],
            target_value=goals_by_type.get(
                NUTRITION_GOAL_TYPES["protein_g"]
            ),
        ),
        carbs_g=build_nutrition_goal_progress_item(
            current_value=totals["carbs_g"],
            target_value=goals_by_type.get(
                NUTRITION_GOAL_TYPES["carbs_g"]
            ),
        ),
        fat_g=build_nutrition_goal_progress_item(
            current_value=totals["fat_g"],
            target_value=goals_by_type.get(
                NUTRITION_GOAL_TYPES["fat_g"]
            ),
        ),
    )

@router.get(
    "/progress",
    response_model=list[FitnessGoalProgressResponse],
)
def get_goals_progress() -> list[FitnessGoalProgressResponse]:
    return build_goals_progress(today=date.today())


@router.get(
    "/nutrition-progress",
    response_model=NutritionGoalsProgressResponse,
)
def get_nutrition_goals_progress(
    target_date: date,
) -> NutritionGoalsProgressResponse:
    return build_nutrition_goals_progress(target_date)


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