import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    BodyCompositionGoalDirection,
    BodyCompositionGoalMetricType,
    BodyCompositionGoalProgressResponse,
    BodyCompositionGoalResponse,
    BodyCompositionGoalUpsert,
    FitnessGoalProgressResponse,
    FitnessGoalResponse,
    FitnessGoalUpsert,
    GoalType,
    NutritionGoalProgressItem,
    NutritionGoalsProgressResponse,
    UserResponse,
)

router = APIRouter(
    prefix="/goals",
    tags=["goals"],
)
BODY_COMPOSITION_METRIC_COLUMNS = {
    "weight_kg": "weight_kg",
    "body_fat_percentage": "body_fat_percentage",
    "waist_cm": "waist_cm",
    "hip_cm": "hip_cm",
    "chest_cm": "chest_cm",
    "arm_cm": "arm_cm",
    "thigh_cm": "thigh_cm",
}

BODY_COMPOSITION_METRIC_MAXIMUMS = {
    "weight_kg": 500,
    "body_fat_percentage": 99.99,
    "waist_cm": 300,
    "hip_cm": 300,
    "chest_cm": 300,
    "arm_cm": 200,
    "thigh_cm": 300,
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
    user_id: int,
) -> float:
    week_start = today - timedelta(days=today.weekday())

    if goal_type == "daily_steps":
        row = connection.execute(
            """
            SELECT COALESCE(steps, 0) AS current_value
            FROM daily_logs
            WHERE date = ? AND user_id = ?
            """,
            (today.isoformat(), user_id),
        ).fetchone()

        return float(row["current_value"]) if row else 0.0

    if goal_type == "weekly_workouts":
        row = connection.execute(
            """
            SELECT COUNT(*) AS current_value
            FROM workout_sessions
            WHERE user_id = ?
              AND date BETWEEN ? AND ?
            """,
            (
                user_id,
                week_start.isoformat(),
                today.isoformat(),
            ),
        ).fetchone()

        return float(row["current_value"])

    if goal_type == "weekly_running_km":
        row = connection.execute(
            """
            SELECT COALESCE(SUM(distance_km), 0) AS current_value
            FROM runs
            WHERE user_id = ?
              AND date BETWEEN ? AND ?
            """,
            (
                user_id,
                week_start.isoformat(),
                today.isoformat(),
            ),
        ).fetchone()

        return float(row["current_value"])

    if goal_type == "daily_sleep_minutes":
        row = connection.execute(
            """
            SELECT COALESCE(sleep_minutes, 0) AS current_value
            FROM daily_recovery_logs
            WHERE date = ? AND user_id = ?
            """,
            (today.isoformat(), user_id),
        ).fetchone()

        return float(row["current_value"]) if row else 0.0

    if goal_type == "weekly_rest_days":
        row = connection.execute(
            """
            SELECT COUNT(*) AS current_value
            FROM daily_recovery_logs
            WHERE date BETWEEN ? AND ?
                AND user_id = ?
                AND is_rest_day = 1
            """,
            (
                week_start.isoformat(),
                today.isoformat(),
                user_id,
            ),
        ).fetchone()

        return float(row["current_value"])

    raise ValueError(f"Tipo de objetivo no compatible: {goal_type}")


def validate_goal_target(
    goal_type: GoalType,
    target_value: float,
) -> None:
    if (
        goal_type == "daily_sleep_minutes"
        and target_value > 1440
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "El objetivo diario de sueño no puede superar "
                "1440 minutos."
            ),
        )

    if (
        goal_type == "weekly_rest_days"
        and (
            not target_value.is_integer()
            or target_value > 7
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "El objetivo semanal de descanso debe ser un "
                "número entero entre 1 y 7."
            ),
        )


@router.put(
    "/{goal_type}",
    response_model=FitnessGoalResponse,
)
def create_or_update_goal(
    goal_type: GoalType,
    goal: FitnessGoalUpsert,
    current_user: UserResponse = Depends(get_current_user),
) -> FitnessGoalResponse:
    validate_goal_target(goal_type, goal.target_value)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO fitness_goals (
                user_id,
                goal_type,
                target_value,
                updated_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, goal_type) DO UPDATE SET
                target_value = excluded.target_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                current_user.id,
                goal_type,
                goal.target_value,
            ),
        )

        row = connection.execute(
            """
            SELECT id, goal_type, target_value
            FROM fitness_goals
            WHERE user_id = ? AND goal_type = ?
            """,
            (current_user.id, goal_type),
        ).fetchone()

    return row_to_fitness_goal(row)


@router.get(
    "/",
    response_model=list[FitnessGoalResponse],
)
def list_goals(
    current_user: UserResponse = Depends(get_current_user),
) -> list[FitnessGoalResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, goal_type, target_value
            FROM fitness_goals
            WHERE user_id = ?
            ORDER BY goal_type ASC
            """,
            (current_user.id,),
        ).fetchall()

    return [row_to_fitness_goal(row) for row in rows]


def build_goals_progress(
    today: date,
    user_id: int,
) -> list[FitnessGoalProgressResponse]:
    progress_items: list[FitnessGoalProgressResponse] = []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT goal_type, target_value
            FROM fitness_goals
            WHERE user_id = ?
                AND goal_type IN (
                    'daily_steps',
                    'weekly_workouts',
                    'weekly_running_km',
                    'daily_sleep_minutes',
                    'weekly_rest_days'
                )
            ORDER BY goal_type ASC
            """,
            (user_id,),
        ).fetchall()

        for row in rows:
            current_value = get_current_value(
                connection=connection,
                goal_type=row["goal_type"],
                today=today,
                user_id=user_id,
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
    user_id: int,
) -> NutritionGoalsProgressResponse:
    with get_connection() as connection:
        totals = get_nutrition_totals(connection, target_date)

        rows = connection.execute(
            """
            SELECT goal_type, target_value
            FROM fitness_goals
            WHERE user_id = ?
                AND goal_type IN (
                    'daily_calories',
                    'daily_protein_g',
                    'daily_carbs_g',
                    'daily_fat_g'
                )
            """,
            (user_id,),
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
def get_goals_progress(
    current_user: UserResponse = Depends(get_current_user),
) -> list[FitnessGoalProgressResponse]:
    return build_goals_progress(
        today=date.today(),
        user_id=current_user.id,
    )


@router.get(
    "/nutrition-progress",
    response_model=NutritionGoalsProgressResponse,
)
def get_nutrition_goals_progress(
    target_date: date,
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionGoalsProgressResponse:
    return build_nutrition_goals_progress(
        target_date=target_date,
        user_id=current_user.id,
    )

@router.get(
    "/body-composition/progress",
    response_model=list[BodyCompositionGoalProgressResponse],
)
def get_body_composition_goals_progress(
    current_user: UserResponse = Depends(get_current_user),
) -> list[BodyCompositionGoalProgressResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                metric_type,
                target_value,
                direction,
                start_value,
                started_at
            FROM body_composition_goals
            WHERE user_id = ?
            ORDER BY metric_type ASC
            """,
            (current_user.id,),
        ).fetchall()

        progress_items: list[BodyCompositionGoalProgressResponse] = []

        for row in rows:
            latest_value = get_latest_body_metric_value(
                connection=connection,
                user_id=current_user.id,
                metric_type=row["metric_type"],
            )

            current_value = (
                latest_value[0] if latest_value is not None else None
            )
            current_value_date = (
                latest_value[1] if latest_value is not None else None
            )
            start_value = (
                float(row["start_value"])
                if row["start_value"] is not None
                else None
            )
            target_value = float(row["target_value"])

            progress_items.append(
                BodyCompositionGoalProgressResponse(
                    metric_type=row["metric_type"],
                    direction=row["direction"],
                    start_value=start_value,
                    current_value=current_value,
                    current_value_date=current_value_date,
                    target_value=target_value,
                    remaining_value=get_body_composition_remaining_value(
                        direction=row["direction"],
                        current_value=current_value,
                        target_value=target_value,
                    ),
                    progress_percentage=get_body_composition_progress_percentage(
                        direction=row["direction"],
                        start_value=start_value,
                        current_value=current_value,
                        target_value=target_value,
                    ),
                    is_completed=is_body_composition_goal_completed(
                        direction=row["direction"],
                        current_value=current_value,
                        target_value=target_value,
                    ),
                )
            )

    return progress_items


@router.get(
    "/body-composition",
    response_model=list[BodyCompositionGoalResponse],
)
def list_body_composition_goals(
    current_user: UserResponse = Depends(get_current_user),
) -> list[BodyCompositionGoalResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                metric_type,
                target_value,
                direction,
                start_value,
                started_at
            FROM body_composition_goals
            WHERE user_id = ?
            ORDER BY metric_type ASC
            """,
            (current_user.id,),
        ).fetchall()

    return [row_to_body_composition_goal(row) for row in rows]


@router.put(
    "/body-composition/{metric_type}",
    response_model=BodyCompositionGoalResponse,
)
def create_or_update_body_composition_goal(
    metric_type: BodyCompositionGoalMetricType,
    goal: BodyCompositionGoalUpsert,
    current_user: UserResponse = Depends(get_current_user),
) -> BodyCompositionGoalResponse:
    with get_connection() as connection:
        existing_row = connection.execute(
            """
            SELECT start_value, started_at
            FROM body_composition_goals
            WHERE user_id = ? AND metric_type = ?
            """,
            (current_user.id, metric_type),
        ).fetchone()

        if goal.start_value is not None:
            start_value = goal.start_value
            started_at = date.today().isoformat()
        elif existing_row is not None:
            start_value = existing_row["start_value"]
            started_at = existing_row["started_at"]
        else:
            latest_value = get_latest_body_metric_value(
                connection,
                user_id=current_user.id,
                metric_type=metric_type,
            )
            start_value = (
                latest_value[0] if latest_value is not None else None
            )
            started_at = date.today().isoformat()

        validate_body_composition_goal(
            metric_type,
            BodyCompositionGoalUpsert(
                target_value=goal.target_value,
                direction=goal.direction,
                start_value=start_value,
            ),
        )

        connection.execute(
            """
            INSERT INTO body_composition_goals (
                user_id,
                metric_type,
                target_value,
                direction,
                start_value,
                started_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, metric_type) DO UPDATE SET
                target_value = excluded.target_value,
                direction = excluded.direction,
                start_value = excluded.start_value,
                started_at = excluded.started_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                current_user.id,
                metric_type,
                goal.target_value,
                goal.direction,
                start_value,
                started_at,
            ),
        )

        row = connection.execute(
            """
            SELECT
                id,
                metric_type,
                target_value,
                direction,
                start_value,
                started_at
            FROM body_composition_goals
            WHERE user_id = ? AND metric_type = ?
            """,
            (current_user.id, metric_type),
        ).fetchone()

    return row_to_body_composition_goal(row)
@router.delete(
    "/body-composition/{metric_type}",
    response_model=None,
)
def delete_body_composition_goal(
    metric_type: BodyCompositionGoalMetricType,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM body_composition_goals
            WHERE user_id = ? AND metric_type = ?
            """,
            (current_user.id, metric_type),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un objetivo corporal de este tipo.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
@router.delete(
    "/{goal_type}",
    response_model=None,
)
def delete_goal(
    goal_type: GoalType,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM fitness_goals
            WHERE user_id = ? AND goal_type = ?
            """,
            (current_user.id, goal_type),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un objetivo de este tipo.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

def row_to_body_composition_goal(
    row: sqlite3.Row,
) -> BodyCompositionGoalResponse:
    return BodyCompositionGoalResponse(
        id=row["id"],
        metric_type=row["metric_type"],
        target_value=float(row["target_value"]),
        direction=row["direction"],
        start_value=(
            float(row["start_value"])
            if row["start_value"] is not None
            else None
        ),
        started_at=date.fromisoformat(row["started_at"]),
    )


def validate_body_composition_goal(
    metric_type: BodyCompositionGoalMetricType,
    goal: BodyCompositionGoalUpsert,
) -> None:
    maximum = BODY_COMPOSITION_METRIC_MAXIMUMS[metric_type]

    if goal.target_value > maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"El objetivo de {metric_type} no puede superar "
                f"{maximum}."
            ),
        )

    if goal.start_value is not None and goal.start_value > maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"El valor inicial de {metric_type} no puede superar "
                f"{maximum}."
            ),
        )

    if goal.start_value is None:
        return

    if (
        goal.direction == "decrease"
        and goal.target_value >= goal.start_value
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Un objetivo de reducción debe ser menor que "
                "el valor inicial."
            ),
        )

    if (
        goal.direction == "increase"
        and goal.target_value <= goal.start_value
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Un objetivo de aumento debe ser mayor que "
                "el valor inicial."
            ),
        )


def get_latest_body_metric_value(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    metric_type: BodyCompositionGoalMetricType,
) -> tuple[float, date] | None:
    metric_column = BODY_COMPOSITION_METRIC_COLUMNS[metric_type]

    row = connection.execute(
        f"""
        SELECT date, {metric_column} AS value
        FROM body_metrics
        WHERE user_id = ?
          AND {metric_column} IS NOT NULL
        ORDER BY date DESC, id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row is None:
        return None

    return float(row["value"]), date.fromisoformat(row["date"])


def get_body_composition_progress_percentage(
    *,
    direction: BodyCompositionGoalDirection,
    start_value: float | None,
    current_value: float | None,
    target_value: float,
) -> float | None:
    if (
        start_value is None
        or current_value is None
        or direction == "maintain"
    ):
        return None

    total_change = target_value - start_value
    current_change = current_value - start_value

    if total_change == 0:
        return None

    return round(
        min(max((current_change / total_change) * 100, 0), 100),
        1,
    )


def get_body_composition_remaining_value(
    *,
    direction: BodyCompositionGoalDirection,
    current_value: float | None,
    target_value: float,
) -> float | None:
    if current_value is None:
        return None

    if direction == "decrease":
        return round(max(current_value - target_value, 0), 2)

    if direction == "increase":
        return round(max(target_value - current_value, 0), 2)

    return round(abs(current_value - target_value), 2)


def is_body_composition_goal_completed(
    *,
    direction: BodyCompositionGoalDirection,
    current_value: float | None,
    target_value: float,
) -> bool:
    if current_value is None:
        return False

    if direction == "decrease":
        return current_value <= target_value

    if direction == "increase":
        return current_value >= target_value

    return current_value == target_value