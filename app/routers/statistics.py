from datetime import date, timedelta

from fastapi import APIRouter, Depends,HTTPException, Query, status

from app.db import get_connection
from app.dependencies import get_current_user

from app.schemas import (
    ActivityChartsResponse,
    ActivityConsistencyResponse,
    ActivityStatisticsResponse,
    ConsistencyMetricResponse,
    StatisticsBodyMetricResponse,
    StatisticsBodyMetricsResponse,
    StatisticsComparisonMetric,
    StatisticsComparisonResponse,
    StatisticsRunningChartPoint,
    StatisticsRunningResponse,
    StatisticsStepsChartPoint,
    StatisticsStepsResponse,
    StatisticsTrendPoint,
    StatisticsTrendsResponse,
    StatisticsWeightChartPoint,
    StatisticsWorkoutVolumeChartPoint,
    StatisticsWorkoutVolumeResponse,
    StatisticsWorkoutsResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/statistics",
    tags=["activity statistics"],
)

MOVING_AVERAGE_WINDOWS = (7, 14, 28)


def validate_date_range(
    start_date: date,
    end_date: date,
) -> None:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )


def iterate_dates(
    start_date: date,
    end_date: date,
) -> list[date]:
    total_days = (end_date - start_date).days + 1

    return [
        start_date + timedelta(days=offset)
        for offset in range(total_days)
    ]


def calculate_moving_average(
    values: list[float | None],
    index: int,
    window: int,
    *,
    include_missing_as_zero: bool,
) -> float | None:
    start_index = max(0, index - window + 1)
    window_values = values[start_index : index + 1]

    if include_missing_as_zero:
        first_recorded_index = next(
            (
                value_index
                for value_index, value in enumerate(window_values)
                if value is not None
            ),
            None,
        )

        if first_recorded_index is None:
            return 0.0

        active_history = window_values[first_recorded_index:]

        values_with_zeroes = [
            value if value is not None else 0.0
            for value in active_history
        ]

        return round(
            sum(values_with_zeroes) / len(values_with_zeroes),
            2,
        )

    available_values = [
        value
        for value in window_values
        if value is not None
    ]

    if not available_values:
        return None

    return round(
        sum(available_values) / len(available_values),
        2,
    )

def build_trend_points(
    *,
    visible_dates: list[date],
    calculation_dates: list[date],
    values_by_date: dict[date, float | None],
    include_missing_as_zero: bool,
) -> list[StatisticsTrendPoint]:
    calculation_values = [
        values_by_date.get(current_date)
        for current_date in calculation_dates
    ]

    calculation_index_by_date = {
        current_date: index
        for index, current_date in enumerate(calculation_dates)
    }

    points: list[StatisticsTrendPoint] = []

    for current_date in visible_dates:
        calculation_index = calculation_index_by_date[current_date]
        value = values_by_date.get(
            current_date,
            0.0 if include_missing_as_zero else None,
        )

        points.append(
            StatisticsTrendPoint(
                date=current_date,
                value=(
                    round(value, 2)
                    if value is not None
                    else None
                ),
                moving_average_7=calculate_moving_average(
                    calculation_values,
                    calculation_index,
                    7,
                    include_missing_as_zero=include_missing_as_zero,
                ),
                moving_average_14=calculate_moving_average(
                    calculation_values,
                    calculation_index,
                    14,
                    include_missing_as_zero=include_missing_as_zero,
                ),
                moving_average_28=calculate_moving_average(
                    calculation_values,
                    calculation_index,
                    28,
                    include_missing_as_zero=include_missing_as_zero,
                ),
            )
        )

    return points


def get_steps_by_date(
    connection,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> dict[date, float]:
    rows = connection.execute(
        """
        SELECT date, steps
        FROM daily_logs
        WHERE user_id = ?
          AND date BETWEEN ? AND ?
        ORDER BY date ASC, id ASC
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchall()

    return {
        date.fromisoformat(row["date"]): float(row["steps"])
        for row in rows
    }


def get_workout_volume_by_date(
    connection,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> dict[date, float]:
    rows = connection.execute(
        """
        SELECT
            workout_sessions.date AS date,
            COALESCE(
                SUM(
                    workout_sets.repetitions
                    * workout_sets.weight_kg
                ),
                0
            ) AS volume_kg
        FROM workout_sessions
        JOIN workout_exercises
            ON workout_exercises.workout_session_id = workout_sessions.id
        JOIN workout_sets
            ON workout_sets.workout_exercise_id = workout_exercises.id
           AND workout_sets.set_type = 'working'
        WHERE workout_sessions.user_id = ?
          AND workout_sessions.date BETWEEN ? AND ?
        GROUP BY workout_sessions.date
        ORDER BY workout_sessions.date ASC
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchall()

    return {
        date.fromisoformat(row["date"]): float(row["volume_kg"])
        for row in rows
    }


def get_running_by_date(
    connection,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> tuple[dict[date, float], dict[date, float | None]]:
    rows = connection.execute(
        """
        SELECT
            date,
            COALESCE(SUM(distance_km), 0) AS distance_km,
            COALESCE(SUM(duration_seconds), 0) AS duration_seconds
        FROM runs
        WHERE user_id = ?
          AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date ASC
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchall()

    distance_by_date: dict[date, float] = {}
    pace_by_date: dict[date, float | None] = {}

    for row in rows:
        current_date = date.fromisoformat(row["date"])
        distance_km = float(row["distance_km"])
        duration_seconds = float(row["duration_seconds"])

        distance_by_date[current_date] = round(distance_km, 2)
        pace_by_date[current_date] = (
            round(duration_seconds / distance_km, 2)
            if distance_km > 0
            else None
        )

    return distance_by_date, pace_by_date


def get_period_totals(
    connection,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, float | None]:
    steps_row = connection.execute(
        """
        SELECT COALESCE(SUM(steps), 0) AS value
        FROM daily_logs
        WHERE user_id = ?
          AND date BETWEEN ? AND ?
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchone()

    workout_volume_row = connection.execute(
        """
        SELECT COALESCE(
            SUM(
                workout_sets.repetitions
                * workout_sets.weight_kg
            ),
            0
        ) AS value
        FROM workout_sessions
        JOIN workout_exercises
            ON workout_exercises.workout_session_id = workout_sessions.id
        JOIN workout_sets
            ON workout_sets.workout_exercise_id = workout_exercises.id
           AND workout_sets.set_type = 'working'
        WHERE workout_sessions.user_id = ?
          AND workout_sessions.date BETWEEN ? AND ?
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchone()

    running_row = connection.execute(
        """
        SELECT
            COALESCE(SUM(distance_km), 0) AS distance_km,
            COALESCE(SUM(duration_seconds), 0) AS duration_seconds
        FROM runs
        WHERE user_id = ?
          AND date BETWEEN ? AND ?
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchone()
    latest_body_metric_row = connection.execute(
        """
        SELECT weight_kg, bmi, body_fat_percentage
        FROM body_metrics
        WHERE user_id = ?
        AND date BETWEEN ? AND ?
        ORDER BY date DESC, id DESC
        LIMIT 1
        """,
        (
            user_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    ).fetchone()
    running_distance_km = float(running_row["distance_km"])
    running_duration_seconds = float(running_row["duration_seconds"])

    return {
        "steps": float(steps_row["value"]),
        "workout_volume_kg": round(
            float(workout_volume_row["value"]),
            2,
        ),
        "running_distance_km": round(running_distance_km, 2),
        "running_average_pace_seconds_km": (
            round(
                running_duration_seconds / running_distance_km,
                2,
            )
            if running_distance_km > 0
            else None
        ),
        "weight_kg": (
            round(float(latest_body_metric_row["weight_kg"]), 2)
            if latest_body_metric_row is not None
            else None
        ),
        "bmi": (
            round(float(latest_body_metric_row["bmi"]), 2)
            if latest_body_metric_row is not None
            else None
        ),
        "body_fat_percentage": (
            round(float(latest_body_metric_row["body_fat_percentage"]), 2)
            if (
                latest_body_metric_row is not None
                and latest_body_metric_row["body_fat_percentage"] is not None
            )
            else None
        ),
    }


def build_comparison_metric(
    *,
    current_value: float | None,
    previous_value: float | None,
) -> StatisticsComparisonMetric:
    if current_value is None or previous_value is None:
        return StatisticsComparisonMetric(
            current_value=current_value,
            previous_value=previous_value,
            absolute_change=None,
            percentage_change=None,
        )

    absolute_change = round(current_value - previous_value, 2)
    percentage_change = (
        round((absolute_change / previous_value) * 100, 1)
        if previous_value != 0
        else None
    )

    return StatisticsComparisonMetric(
        current_value=current_value,
        previous_value=previous_value,
        absolute_change=absolute_change,
        percentage_change=percentage_change,
    )

@router.get(
    "/summary",
    response_model=ActivityStatisticsResponse,
)
def get_activity_statistics(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> ActivityStatisticsResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    start_date_value = start_date.isoformat()
    end_date_value = end_date.isoformat()

    with get_connection() as connection:
        steps_row = connection.execute(
            """
            SELECT
                COUNT(*) AS days_logged,
                COALESCE(SUM(steps), 0) AS total_steps
            FROM daily_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchone()

        workouts_row = connection.execute(
            """
            SELECT
                COUNT(DISTINCT workout_sessions.id) AS sessions,
                COUNT(DISTINCT workout_exercises.id) AS exercises,
                COUNT(workout_sets.id) AS working_sets,
                COALESCE(SUM(workout_sets.repetitions), 0) AS repetitions,
                TOTAL(
                    workout_sets.repetitions * workout_sets.weight_kg
                ) AS volume_kg
            FROM workout_sessions
            LEFT JOIN workout_exercises
                ON workout_exercises.workout_session_id = workout_sessions.id
            LEFT JOIN workout_sets
                ON workout_sets.workout_exercise_id = workout_exercises.id
                AND workout_sets.set_type = 'working'
            WHERE workout_sessions.user_id = ? AND workout_sessions.date BETWEEN ? AND ?
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchone()

        running_row = connection.execute(
            """
            SELECT
                COUNT(*) AS runs,
                COALESCE(TOTAL(distance_km), 0) AS distance_km,
                COALESCE(SUM(duration_seconds), 0) AS duration_seconds
            FROM runs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchone()

        body_metrics_count_row = connection.execute(
            """
            SELECT COUNT(*) AS records
            FROM body_metrics
            WHERE user_id = ? AND date BETWEEN ? AND ?
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchone()

        first_body_metric_row = connection.execute(
            """
            SELECT date, weight_kg, height_cm, bmi
            FROM body_metrics
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            LIMIT 1
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchone()

        latest_body_metric_row = connection.execute(
            """
            SELECT date, weight_kg, height_cm, bmi
            FROM body_metrics
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchone()

    days_logged = steps_row["days_logged"]
    total_steps = steps_row["total_steps"]

    distance_km = float(running_row["distance_km"])
    duration_seconds = running_row["duration_seconds"]

    average_pace_seconds_km = None
    if distance_km > 0:
        average_pace_seconds_km = round(
            duration_seconds / distance_km,
            2,
        )

    latest_body_metric = None
    if latest_body_metric_row is not None:
        latest_body_metric = StatisticsBodyMetricResponse(
            date=date.fromisoformat(latest_body_metric_row["date"]),
            weight_kg=latest_body_metric_row["weight_kg"],
            height_cm=latest_body_metric_row["height_cm"],
            bmi=latest_body_metric_row["bmi"],
        )

    weight_change_kg = None
    if first_body_metric_row is not None and latest_body_metric_row is not None:
        weight_change_kg = round(
            latest_body_metric_row["weight_kg"]
            - first_body_metric_row["weight_kg"],
            2,
        )

    return ActivityStatisticsResponse(
        start_date=start_date,
        end_date=end_date,
        steps=StatisticsStepsResponse(
            total=total_steps,
            days_logged=days_logged,
            average_per_logged_day=round(total_steps / days_logged, 2)
            if days_logged > 0
            else 0.0,
        ),
        workouts=StatisticsWorkoutsResponse(
            sessions=workouts_row["sessions"],
            exercises=workouts_row["exercises"],
            working_sets=workouts_row["working_sets"],
            repetitions=workouts_row["repetitions"],
            volume_kg=round(workouts_row["volume_kg"], 2),
        ),
        running=StatisticsRunningResponse(
            runs=running_row["runs"],
            distance_km=round(distance_km, 2),
            duration_seconds=duration_seconds,
            average_pace_seconds_km=average_pace_seconds_km,
        ),
        body_metrics=StatisticsBodyMetricsResponse(
            records=body_metrics_count_row["records"],
            latest=latest_body_metric,
            weight_change_kg=weight_change_kg,
        ),
    )
@router.get(
    "/charts",
    response_model=ActivityChartsResponse,
)
def get_activity_charts(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> ActivityChartsResponse:
    validate_date_range(start_date, end_date)

    start_date_value = start_date.isoformat()
    end_date_value = end_date.isoformat()

    with get_connection() as connection:
        steps_rows = connection.execute(
            """
            SELECT date, steps
            FROM daily_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

        weight_rows = connection.execute(
            """
            SELECT date, weight_kg
            FROM body_metrics
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

        running_rows = connection.execute(
            """
            SELECT
                date,
                ROUND(SUM(distance_km), 2) AS distance_km
            FROM runs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

    return ActivityChartsResponse(
        start_date=start_date,
        end_date=end_date,
        steps=[
            StatisticsStepsChartPoint(
                date=date.fromisoformat(row["date"]),
                steps=row["steps"],
            )
            for row in steps_rows
        ],
        weight=[
            StatisticsWeightChartPoint(
                date=date.fromisoformat(row["date"]),
                weight_kg=row["weight_kg"],
            )
            for row in weight_rows
        ],
        running=[
            StatisticsRunningChartPoint(
                date=date.fromisoformat(row["date"]),
                distance_km=row["distance_km"],
            )
            for row in running_rows
        ],
    )
@router.get(
    "/trends",
    response_model=StatisticsTrendsResponse,
)
def get_statistics_trends(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> StatisticsTrendsResponse:
    validate_date_range(start_date, end_date)

    calculation_start_date = start_date - timedelta(days=27)
    calculation_dates = iterate_dates(
        calculation_start_date,
        end_date,
    )
    visible_dates = iterate_dates(start_date, end_date)

    with get_connection() as connection:
        steps_by_date = get_steps_by_date(
            connection,
            user_id=current_user.id,
            start_date=calculation_start_date,
            end_date=end_date,
        )
        workout_volume_by_date = get_workout_volume_by_date(
            connection,
            user_id=current_user.id,
            start_date=calculation_start_date,
            end_date=end_date,
        )
        (
            running_distance_by_date,
            running_pace_by_date,
        ) = get_running_by_date(
            connection,
            user_id=current_user.id,
            start_date=calculation_start_date,
            end_date=end_date,
        )

    return StatisticsTrendsResponse(
        start_date=start_date,
        end_date=end_date,
        steps=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=steps_by_date,
            include_missing_as_zero=True,
        ),
        workout_volume_kg=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=workout_volume_by_date,
            include_missing_as_zero=True,
        ),
        running_distance_km=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=running_distance_by_date,
            include_missing_as_zero=True,
        ),
        running_pace_seconds_km=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=running_pace_by_date,
            include_missing_as_zero=False,
        ),
    )
@router.get(
    "/workout-volume",
    response_model=StatisticsWorkoutVolumeResponse,
)
def get_statistics_workout_volume(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> StatisticsWorkoutVolumeResponse:
    validate_date_range(start_date, end_date)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                workout_sessions.date AS date,
                ROUND(
                    COALESCE(
                        SUM(
                            workout_sets.repetitions
                            * workout_sets.weight_kg
                        ),
                        0
                    ),
                    2
                ) AS volume_kg,
                COUNT(workout_sets.id) AS working_sets,
                COALESCE(
                    SUM(workout_sets.repetitions),
                    0
                ) AS repetitions
            FROM workout_sessions
            JOIN workout_exercises
                ON workout_exercises.workout_session_id = workout_sessions.id
            JOIN workout_sets
                ON workout_sets.workout_exercise_id = workout_exercises.id
               AND workout_sets.set_type = 'working'
            WHERE workout_sessions.user_id = ?
              AND workout_sessions.date BETWEEN ? AND ?
            GROUP BY workout_sessions.date
            ORDER BY workout_sessions.date ASC
            """,
            (
                current_user.id,
                start_date.isoformat(),
                end_date.isoformat(),
            ),
        ).fetchall()

    return StatisticsWorkoutVolumeResponse(
        start_date=start_date,
        end_date=end_date,
        records=[
            StatisticsWorkoutVolumeChartPoint(
                date=date.fromisoformat(row["date"]),
                volume_kg=float(row["volume_kg"]),
                working_sets=row["working_sets"],
                repetitions=row["repetitions"],
            )
            for row in rows
        ],
    )
@router.get(
    "/comparison",
    response_model=StatisticsComparisonResponse,
)
def get_statistics_comparison(
    start_date: date = Query(
        description="Fecha inicial del periodo actual, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo actual, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> StatisticsComparisonResponse:
    validate_date_range(start_date, end_date)

    period_days = (end_date - start_date).days + 1
    previous_end_date = start_date - timedelta(days=1)
    previous_start_date = previous_end_date - timedelta(
        days=period_days - 1,
    )

    with get_connection() as connection:
        current_totals = get_period_totals(
            connection,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        previous_totals = get_period_totals(
            connection,
            user_id=current_user.id,
            start_date=previous_start_date,
            end_date=previous_end_date,
        )

    return StatisticsComparisonResponse(
        current_start_date=start_date,
        current_end_date=end_date,
        previous_start_date=previous_start_date,
        previous_end_date=previous_end_date,
        steps=build_comparison_metric(
            current_value=current_totals["steps"],
            previous_value=previous_totals["steps"],
        ),
        workout_volume_kg=build_comparison_metric(
            current_value=current_totals["workout_volume_kg"],
            previous_value=previous_totals["workout_volume_kg"],
        ),
        running_distance_km=build_comparison_metric(
            current_value=current_totals["running_distance_km"],
            previous_value=previous_totals["running_distance_km"],
        ),
        running_average_pace_seconds_km=build_comparison_metric(
            current_value=current_totals[
                "running_average_pace_seconds_km"
            ],
            previous_value=previous_totals[
                "running_average_pace_seconds_km"
            ],
        ),
        weight_kg=build_comparison_metric(
            current_value=current_totals["weight_kg"],
            previous_value=previous_totals["weight_kg"],
        ),
        bmi=build_comparison_metric(
            current_value=current_totals["bmi"],
            previous_value=previous_totals["bmi"],
        ),
        body_fat_percentage=build_comparison_metric(
            current_value=current_totals["body_fat_percentage"],
            previous_value=previous_totals["body_fat_percentage"],
        ),
    )
def get_statistics_comparison(
    start_date: date = Query(
        description="Fecha inicial del periodo actual, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo actual, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> StatisticsComparisonResponse:
    validate_date_range(start_date, end_date)

    period_days = (end_date - start_date).days + 1
    previous_end_date = start_date - timedelta(days=1)
    previous_start_date = previous_end_date - timedelta(
        days=period_days - 1,
    )

    with get_connection() as connection:
        current_totals = get_period_totals(
            connection,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        previous_totals = get_period_totals(
            connection,
            user_id=current_user.id,
            start_date=previous_start_date,
            end_date=previous_end_date,
        )

    return StatisticsComparisonResponse(
        current_start_date=start_date,
        current_end_date=end_date,
        previous_start_date=previous_start_date,
        previous_end_date=previous_end_date,
        steps=build_comparison_metric(
            current_value=current_totals["steps"],
            previous_value=previous_totals["steps"],
        ),
        workout_volume_kg=build_comparison_metric(
            current_value=current_totals["workout_volume_kg"],
            previous_value=previous_totals["workout_volume_kg"],
        ),
        running_distance_km=build_comparison_metric(
            current_value=current_totals["running_distance_km"],
            previous_value=previous_totals["running_distance_km"],
        ),
        running_average_pace_seconds_km=build_comparison_metric(
            current_value=(
                current_totals[
                    "running_average_pace_seconds_km"
                ]
            ),
            previous_value=(
                previous_totals[
                    "running_average_pace_seconds_km"
                ]
            ),
        ),
        weight_kg=build_comparison_metric(
            current_value=current_totals["weight_kg"],
            previous_value=previous_totals["weight_kg"],
        ),
    )
def get_statistics_workout_volume(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> StatisticsWorkoutVolumeResponse:
    validate_date_range(start_date, end_date)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                workout_sessions.date AS date,
                ROUND(
                    COALESCE(
                        SUM(
                            workout_sets.repetitions
                            * workout_sets.weight_kg
                        ),
                        0
                    ),
                    2
                ) AS volume_kg,
                COUNT(workout_sets.id) AS working_sets,
                COALESCE(
                    SUM(workout_sets.repetitions),
                    0
                ) AS repetitions
            FROM workout_sessions
            JOIN workout_exercises
                ON workout_exercises.workout_session_id = workout_sessions.id
            JOIN workout_sets
                ON workout_sets.workout_exercise_id = workout_exercises.id
               AND workout_sets.set_type = 'working'
            WHERE workout_sessions.user_id = ?
              AND workout_sessions.date BETWEEN ? AND ?
            GROUP BY workout_sessions.date
            ORDER BY workout_sessions.date ASC
            """,
            (
                current_user.id,
                start_date.isoformat(),
                end_date.isoformat(),
            ),
        ).fetchall()

    return StatisticsWorkoutVolumeResponse(
        start_date=start_date,
        end_date=end_date,
        records=[
            StatisticsWorkoutVolumeChartPoint(
                date=date.fromisoformat(row["date"]),
                volume_kg=float(row["volume_kg"]),
                working_sets=row["working_sets"],
                repetitions=row["repetitions"],
            )
            for row in rows
        ],
    )
def get_statistics_trends(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> StatisticsTrendsResponse:
    validate_date_range(start_date, end_date)

    calculation_start_date = start_date - timedelta(days=27)
    calculation_dates = iterate_dates(
        calculation_start_date,
        end_date,
    )
    visible_dates = iterate_dates(start_date, end_date)

    with get_connection() as connection:
        steps_by_date = get_steps_by_date(
            connection,
            user_id=current_user.id,
            start_date=calculation_start_date,
            end_date=end_date,
        )
        workout_volume_by_date = get_workout_volume_by_date(
            connection,
            user_id=current_user.id,
            start_date=calculation_start_date,
            end_date=end_date,
        )
        (
            running_distance_by_date,
            running_pace_by_date,
        ) = get_running_by_date(
            connection,
            user_id=current_user.id,
            start_date=calculation_start_date,
            end_date=end_date,
        )

    return StatisticsTrendsResponse(
        start_date=start_date,
        end_date=end_date,
        steps=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=steps_by_date,
            include_missing_as_zero=True,
        ),
        workout_volume_kg=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=workout_volume_by_date,
            include_missing_as_zero=True,
        ),
        running_distance_km=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=running_distance_by_date,
            include_missing_as_zero=True,
        ),
        running_pace_seconds_km=build_trend_points(
            visible_dates=visible_dates,
            calculation_dates=calculation_dates,
            values_by_date=running_pace_by_date,
            include_missing_as_zero=False,
        ),
    )
def get_activity_charts(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> ActivityChartsResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    start_date_value = start_date.isoformat()
    end_date_value = end_date.isoformat()

    with get_connection() as connection:
        steps_rows = connection.execute(
            """
            SELECT date, steps
            FROM daily_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

        weight_rows = connection.execute(
            """
            SELECT date, weight_kg
            FROM body_metrics
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

        running_rows = connection.execute(
            """
            SELECT
                date,
                ROUND(SUM(distance_km), 2) AS distance_km
            FROM runs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

    return ActivityChartsResponse(
        start_date=start_date,
        end_date=end_date,
        steps=[
            StatisticsStepsChartPoint(
                date=date.fromisoformat(row["date"]),
                steps=row["steps"],
            )
            for row in steps_rows
        ],
        weight=[
            StatisticsWeightChartPoint(
                date=date.fromisoformat(row["date"]),
                weight_kg=row["weight_kg"],
            )
            for row in weight_rows
        ],
        running=[
            StatisticsRunningChartPoint(
                date=date.fromisoformat(row["date"]),
                distance_km=row["distance_km"],
            )
            for row in running_rows
        ],
    )

def get_consecutive_streaks(
    *,
    start_date: date,
    end_date: date,
    completed_dates: set[date],
) -> tuple[int, int]:
    best_streak = 0
    current_run = 0
    day = start_date

    while day <= end_date:
        if day in completed_dates:
            current_run += 1
            best_streak = max(best_streak, current_run)
        else:
            current_run = 0

        day += timedelta(days=1)

    current_streak = 0
    day = end_date

    while day >= start_date and day in completed_dates:
        current_streak += 1
        day -= timedelta(days=1)

    return current_streak, best_streak


def build_consistency_metric(
    *,
    start_date: date,
    end_date: date,
    period_days: int,
    goal_target: float | None,
    logged_dates: set[date],
    completed_dates: set[date],

) -> ConsistencyMetricResponse:
    if goal_target is None:
        return ConsistencyMetricResponse(
            goal_target=None,
            days_logged=len(logged_dates),
            goal_days_met=None,
            consistency_percentage=None,
            current_streak=None,
            best_streak=None,
        )

    current_streak, best_streak = get_consecutive_streaks(
        start_date=start_date,
        end_date=end_date,
        completed_dates=completed_dates,
    )

    return ConsistencyMetricResponse(
        goal_target=goal_target,
        days_logged=len(logged_dates),
        goal_days_met=len(completed_dates),
        consistency_percentage=round(
            (len(completed_dates) / period_days) * 100,
            1,
        ),
        current_streak=current_streak,
        best_streak=best_streak,
    )


@router.get(
    "/consistency",
    response_model=ActivityConsistencyResponse,
)
def get_activity_consistency(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> ActivityConsistencyResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    start_date_value = start_date.isoformat()
    end_date_value = end_date.isoformat()
    period_days = (end_date - start_date).days + 1

    with get_connection() as connection:
        goal_rows = connection.execute(
            """
            SELECT goal_type, target_value
            FROM fitness_goals
            WHERE user_id = ?
              AND goal_type IN (
                  'daily_steps',
                  'daily_sleep_minutes'
              )
            """,
            (current_user.id,),
        ).fetchall()

        step_rows = connection.execute(
            """
            SELECT date, steps
            FROM daily_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

        sleep_rows = connection.execute(
            """
            SELECT date, sleep_minutes
            FROM daily_recovery_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
                AND sleep_minutes IS NOT NULL
            """,
            (current_user.id, start_date_value, end_date_value),
        ).fetchall()

    goals_by_type = {
        row["goal_type"]: float(row["target_value"])
        for row in goal_rows
    }

    steps_goal_target = goals_by_type.get("daily_steps")
    sleep_goal_target = goals_by_type.get("daily_sleep_minutes")

    steps_logged_dates = {
        date.fromisoformat(row["date"])
        for row in step_rows
    }
    steps_completed_dates = {
        date.fromisoformat(row["date"])
        for row in step_rows
        if (
            steps_goal_target is not None
            and row["steps"] >= steps_goal_target
        )
    }

    sleep_logged_dates = {
        date.fromisoformat(row["date"])
        for row in sleep_rows
    }
    sleep_completed_dates = {
        date.fromisoformat(row["date"])
        for row in sleep_rows
        if (
            sleep_goal_target is not None
            and row["sleep_minutes"] >= sleep_goal_target
        )
    }

    return ActivityConsistencyResponse(
        start_date=start_date,
        end_date=end_date,
        period_days=period_days,
        steps=build_consistency_metric(
            start_date=start_date,
            end_date=end_date,
            period_days=period_days,
            goal_target=steps_goal_target,
            logged_dates=steps_logged_dates,
            completed_dates=steps_completed_dates,
        ),
        sleep=build_consistency_metric(
            start_date=start_date,
            end_date=end_date,
            period_days=period_days,
            goal_target=sleep_goal_target,
            logged_dates=sleep_logged_dates,
            completed_dates=sleep_completed_dates,
        ),
    )