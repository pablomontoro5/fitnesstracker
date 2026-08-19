from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.db import get_connection
from app.schemas import (
    ActivityStatisticsResponse,
    StatisticsBodyMetricResponse,
    StatisticsBodyMetricsResponse,
    StatisticsRunningResponse,
    StatisticsStepsResponse,
    StatisticsWorkoutsResponse,
)


router = APIRouter(
    prefix="/statistics",
    tags=["activity statistics"],
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
            WHERE date BETWEEN ? AND ?
            """,
            (start_date_value, end_date_value),
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
            WHERE workout_sessions.date BETWEEN ? AND ?
            """,
            (start_date_value, end_date_value),
        ).fetchone()

        running_row = connection.execute(
            """
            SELECT
                COUNT(*) AS runs,
                TOTAL(distance_km) AS distance_km,
                COALESCE(SUM(duration_seconds), 0) AS duration_seconds
            FROM runs
            WHERE date BETWEEN ? AND ?
            """,
            (start_date_value, end_date_value),
        ).fetchone()

        body_metrics_count_row = connection.execute(
            """
            SELECT COUNT(*) AS records
            FROM body_metrics
            WHERE date BETWEEN ? AND ?
            """,
            (start_date_value, end_date_value),
        ).fetchone()

        first_body_metric_row = connection.execute(
            """
            SELECT date, weight_kg, height_cm, bmi
            FROM body_metrics
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            LIMIT 1
            """,
            (start_date_value, end_date_value),
        ).fetchone()

        latest_body_metric_row = connection.execute(
            """
            SELECT date, weight_kg, height_cm, bmi
            FROM body_metrics
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (start_date_value, end_date_value),
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