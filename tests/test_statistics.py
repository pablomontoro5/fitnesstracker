from fastapi.testclient import TestClient
from datetime import date
from app.main import app

import pytest

from app.db import get_connection

from app.routers.statistics import get_consecutive_streaks
def register_and_login(
    client: TestClient,
    *,
    email: str = "ana@example.com",
    display_name: str = "Ana",
) -> dict[str, str]:
    password = "password-segura-123"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": display_name,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }
@pytest.fixture(autouse=True)
def clear_statistics_test_data():
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM daily_logs
            WHERE date IN ('2026-09-30', '2026-10-01', '2026-11-01')
            """
        )
        connection.execute(
            """
            DELETE FROM daily_recovery_logs
            WHERE date IN (
                '2026-09-28',
                '2026-09-29',
                '2026-09-30',
                '2026-10-01',
                '2026-10-02',
                '2026-11-01'
            )
            """
        )

        connection.execute(
            """
            DELETE FROM runs
            WHERE date IN ('2026-09-30', '2026-10-01', '2026-11-01')
            """
        )

        connection.execute(
            """
            DELETE FROM body_metrics
            WHERE date IN ('2026-09-30', '2026-10-01', '2026-11-01')
            """
        )

        connection.execute(
            """
            DELETE FROM workout_sessions
            WHERE date IN ('2026-09-30', '2026-10-01', '2026-11-01')
            """
        )

def create_daily_log(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    steps: int,
) -> dict:
    response = client.post(
        "/daily-logs/",
        headers=headers,
        json={
            "date": date,
            "steps": steps,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_recovery_log(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    sleep_minutes: int | None,
) -> dict:
    
    response = client.post(
        "/recovery-logs/",
        headers=headers,
        json={
            "date": date,
            "sleep_minutes": sleep_minutes,
            "sleep_quality": None,
            "is_rest_day": False,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_goal(
    client: TestClient,
    *,
    headers: dict[str, str],
    goal_type: str,
    target_value: float,
) -> dict:
    response = client.put(
        f"/goals/{goal_type}",
        headers=headers,
        json={"target_value": target_value},
    )

    assert response.status_code == 200
    return response.json()
def create_workout_session(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    name: str = "Torso",
) -> dict:
    response = client.post(
        "/workout-sessions/",
        headers=headers,
        json={
            "date": date,
            "name": name,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()

def create_workout_exercise(
    client: TestClient,
    *,
    headers: dict[str, str],
    session_id: int,
    name: str = "Press banca",
    position: int = 1,
) -> dict:
    response = client.post(
        f"/workout-sessions/{session_id}/exercises/",
        json={
            "name": name,
            "muscle_group": "Pecho",
            "position": position,
            "technique_notes": None,
        },
        headers=headers,
    )

    assert response.status_code == 201
    return response.json()


def create_workout_set(
    client: TestClient,
    *,
    headers: dict[str, str],
    exercise_id: int,
    set_type: str = "working",
    position: int = 1,
    repetitions: int = 10,
    weight_kg: float = 50,
) -> dict:
    response = client.post(
        f"/workout-exercises/{exercise_id}/sets/",
        json={
            "set_type": set_type,
            "position": position,
            "target_rep_range": "8-12",
            "repetitions": repetitions,
            "weight_kg": weight_kg,
            "rir": 2,
            "notes": None,
        },
        headers=headers,
    )

    assert response.status_code == 201
    return response.json()


def create_run(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    distance_km: float,
    duration_seconds: int,
) -> dict:
    response = client.post(
        "/runs/",
        headers=headers,
        json={
            "date": date,
            "distance_km": distance_km,
            "duration_seconds": duration_seconds,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_body_metric(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    weight_kg: float,
    height_cm: float = 180,
) -> dict:
    response = client.post(
        "/body-metrics/",
        json={
            "date": date,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "notes": None,
        },
        headers=headers,
    )

    assert response.status_code == 201
    return response.json()


def get_summary(
    client: TestClient,
    *,
    headers: dict[str, str],
    start_date: str = "2026-09-30",
    end_date: str = "2026-10-01",
) -> dict:
    response = client.get(
        "/statistics/summary",
        headers=headers,
        params={
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    assert response.status_code == 200
    return response.json()

def test_statistics_summary_is_empty_when_no_data_exists():
    with TestClient(app) as client:
        headers = register_and_login(client)
        summary = get_summary(client, headers=headers)

    assert summary["start_date"] == "2026-09-30"
    assert summary["end_date"] == "2026-10-01"

    assert summary["steps"] == {
        "total": 0,
        "days_logged": 0,
        "average_per_logged_day": 0,
    }

    assert summary["workouts"] == {
        "sessions": 0,
        "exercises": 0,
        "working_sets": 0,
        "repetitions": 0,
        "volume_kg": 0,
    }

    assert summary["running"] == {
        "runs": 0,
        "distance_km": 0,
        "duration_seconds": 0,
        "average_pace_seconds_km": None,
    }

    assert summary["body_metrics"] == {
        "records": 0,
        "latest": None,
        "weight_change_kg": None,
    }

def test_statistics_summary_aggregates_data_in_period():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_daily_log(
            client,
            headers=headers,
            date="2026-09-30",
            steps=8000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-10-01",
            steps=12000,
        )

        session = create_workout_session(
            client,
            headers=headers,
            date="2026-09-30",
        )
        exercise = create_workout_exercise(
            client,
            headers=headers,
            session_id=session["id"],
        )

        create_workout_set(
            client,
            headers=headers,
            exercise_id=exercise["id"],
            position=1,
            repetitions=10,
            weight_kg=50,
        )
        create_workout_set(
            client,
            headers=headers,
            exercise_id=exercise["id"],
            position=2,
            repetitions=8,
            weight_kg=60,
        )

        create_run(
            client,
            headers=headers,
            date="2026-09-30",
            distance_km=5,
            duration_seconds=1500,
        )
        create_run(
            client,
            headers=headers,
            date="2026-10-01",
            distance_km=10,
            duration_seconds=3600,
        )

        create_body_metric(
            client,
            headers=headers,
            date="2026-09-30",
            weight_kg=80,
        )
        create_body_metric(
            client,
            headers=headers,
            date="2026-10-01",
            weight_kg=79.5,
        )

        summary = get_summary(client, headers=headers)

    assert summary["steps"] == {
        "total": 20000,
        "days_logged": 2,
        "average_per_logged_day": 10000,
    }

    assert summary["workouts"] == {
        "sessions": 1,
        "exercises": 1,
        "working_sets": 2,
        "repetitions": 18,
        "volume_kg": 980,
    }

    assert summary["running"] == {
        "runs": 2,
        "distance_km": 15,
        "duration_seconds": 5100,
        "average_pace_seconds_km": 340,
    }

    assert summary["body_metrics"]["records"] == 2
    assert summary["body_metrics"]["latest"]["date"] == "2026-10-01"
    assert summary["body_metrics"]["latest"]["weight_kg"] == 79.5
    assert summary["body_metrics"]["latest"]["height_cm"] == 180
    assert summary["body_metrics"]["latest"]["bmi"] == 24.54
    assert summary["body_metrics"]["weight_change_kg"] == -0.5


def test_statistics_summary_excludes_data_outside_period():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_daily_log(
            client,
            headers=headers,
            date="2026-09-29",
            steps=9999,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-10-01",
            steps=1000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-11-01",
            steps=8888,
        )

        create_run(
            client,
            headers=headers,
            date="2026-09-29",
            distance_km=50,
            duration_seconds=15000,
        )
        create_run(
            client,
            headers=headers,
            date="2026-10-01",
            distance_km=5,
            duration_seconds=1500,
        )

        summary = get_summary(client, headers=headers)

    assert summary["steps"]["total"] == 1000
    assert summary["steps"]["days_logged"] == 1
    assert summary["running"]["runs"] == 1
    assert summary["running"]["distance_km"] == 5
    assert summary["running"]["duration_seconds"] == 1500
    assert summary["running"]["average_pace_seconds_km"] == 300

def test_statistics_summary_only_counts_working_sets():
    with TestClient(app) as client:
        headers = register_and_login(client)
        session = create_workout_session(
            client,
            headers=headers,
            date="2026-09-30",
        )
        exercise = create_workout_exercise(
            client,
            headers=headers,
            session_id=session["id"],
        )

        create_workout_set(
            client,            
            exercise_id=exercise["id"],
            headers=headers,
            set_type="warmup",
            position=1,
            repetitions=15,
            weight_kg=20,
        )
        create_workout_set(
            client,
            headers=headers,
            exercise_id=exercise["id"],
            set_type="approximation",
            position=2,
            repetitions=8,
            weight_kg=40,
        )
        create_workout_set(
            client,
            headers=headers,
            exercise_id=exercise["id"],
            set_type="working",
            position=3,
            repetitions=10,
            weight_kg=50,
        )
        create_workout_set(
            client,
            headers=headers,
            exercise_id=exercise["id"],
            set_type="drop_set",
            position=4,
            repetitions=12,
            weight_kg=30,
        )

        summary = get_summary(client, headers=headers)

    assert summary["workouts"]["sessions"] == 1
    assert summary["workouts"]["exercises"] == 1
    assert summary["workouts"]["working_sets"] == 1
    assert summary["workouts"]["repetitions"] == 10
    assert summary["workouts"]["volume_kg"] == 500


def test_statistics_summary_rejects_inverted_date_range():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.get(
            "/statistics/summary",
            params={
                "start_date": "2026-10-01",
                "end_date": "2026-09-30",
            },
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "start_date no puede ser posterior a end_date."
    )

def test_statistics_summary_rejects_invalid_date():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.get(
            "/statistics/summary",
            params={
                "start_date": "not-a-date",
                "end_date": "2026-10-01",
            },
            headers=headers ,
        )

    assert response.status_code == 422
def test_statistics_charts_returns_ordered_series_in_period():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_daily_log(
            client,
            headers=headers,
            date="2026-09-30",
            steps=8000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-10-01",
            steps=12000,
        )

        create_body_metric(
            client,
            headers=headers,
            date="2026-09-30",
            weight_kg=80,
        )
        create_body_metric(
            client,
            headers=headers,
            date="2026-10-01",
            weight_kg=79.5,
        )

        create_run(
            client,
            headers=headers,
            date="2026-09-30",
            distance_km=5,
            duration_seconds=1500,
        )
        create_run(
            client,
            headers=headers,
            date="2026-09-30",
            distance_km=2.5,
            duration_seconds=900,
        )
        create_run(
            client,
            headers=headers,
            date="2026-10-01",
            distance_km=10,
            duration_seconds=3600,
        )

        response = client.get(
            "/statistics/charts",
            params={
                "start_date": "2026-09-30",
                "end_date": "2026-10-01",
            },
            headers=headers,
        )

    assert response.status_code == 200

    assert response.json() == {
        "start_date": "2026-09-30",
        "end_date": "2026-10-01",
        "steps": [
            {"date": "2026-09-30", "steps": 8000},
            {"date": "2026-10-01", "steps": 12000},
        ],
        "weight": [
            {"date": "2026-09-30", "weight_kg": 80},
            {"date": "2026-10-01", "weight_kg": 79.5},
        ],
        "running": [
            {"date": "2026-09-30", "distance_km": 7.5},
            {"date": "2026-10-01", "distance_km": 10},
        ],
    }
def test_statistics_charts_rejects_inverted_date_range():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.get(
            "/statistics/charts",
            params={
                "start_date": "2026-10-01",
                "end_date": "2026-09-30",
            },
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "start_date no puede ser posterior a end_date."
    )

def test_get_consecutive_streaks_calculates_current_and_best_streaks():
    current_streak, best_streak = get_consecutive_streaks(
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 7),
        completed_dates={
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 4),
            date(2026, 9, 5),
            date(2026, 9, 6),
            date(2026, 9, 7),
        },
    )

    assert current_streak == 4
    assert best_streak == 4
def test_statistics_consistency_returns_steps_sleep_and_streaks():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_goal(
            client,
            headers=headers,
            goal_type="daily_steps",
            target_value=8000,
        )
        create_goal(
            client,
            headers=headers,
            goal_type="daily_sleep_minutes",
            target_value=480,
        )

        create_daily_log(
            client,
            headers=headers,
            date="2026-09-01",
            steps=8000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-09-02",
            steps=9000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-09-03",
            steps=7000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-09-04",
            steps=8500,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-09-05",
            steps=8000,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-09-06",
            steps=8100,
        )
        create_daily_log(
            client,
            headers=headers,
            date="2026-09-07",
            steps=8300,
        )

        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-01",
            sleep_minutes=480,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-02",
            sleep_minutes=420,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-03",
            sleep_minutes=500,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-04",
            sleep_minutes=None,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-05",
            sleep_minutes=490,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-06",
            sleep_minutes=480,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-07",
            sleep_minutes=510,
        )

        response = client.get(
            "/statistics/consistency",
            headers=headers,
            params={
                "start_date": "2026-09-01",
                "end_date": "2026-09-07",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-07",
        "period_days": 7,
        "steps": {
            "goal_target": 8000,
            "days_logged": 7,
            "goal_days_met": 6,
            "consistency_percentage": 85.7,
            "current_streak": 4,
            "best_streak": 4,
        },
        "sleep": {
            "goal_target": 480,
            "days_logged": 6,
            "goal_days_met": 5,
            "consistency_percentage": 71.4,
            "current_streak": 3,
            "best_streak": 3,
        },
    }

def test_statistics_consistency_returns_null_goal_metrics_without_goals():
    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="sin-metas@example.com",
            display_name="Sin metas",
        )

        create_daily_log(
            client,
            headers=headers,
            date="2026-09-01",
            steps=10000,
        )
        create_recovery_log(
            client,
            headers=headers,
            date="2026-09-01",
            sleep_minutes=480,
        )

        response = client.get(
            "/statistics/consistency",
            headers=headers,
            params={
                "start_date": "2026-09-01",
                "end_date": "2026-09-03",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-03",
        "period_days": 3,
        "steps": {
            "goal_target": None,
            "days_logged": 1,
            "goal_days_met": None,
            "consistency_percentage": None,
            "current_streak": None,
            "best_streak": None,
        },
        "sleep": {
            "goal_target": None,
            "days_logged": 1,
            "goal_days_met": None,
            "consistency_percentage": None,
            "current_streak": None,
            "best_streak": None,
        },
    }
def test_statistics_consistency_rejects_inverted_date_range():
    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="sin-metas@example.com",
            display_name="Sin metas",
        )
        response = client.get(
            "/statistics/consistency",
            params={
                "start_date": "2026-09-02",
                "end_date": "2026-09-01",
            },
            headers=headers
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "start_date no puede ser posterior a end_date."
    )


def test_statistics_only_include_current_user_data():
    with TestClient(app) as client:
        owner_headers = register_and_login(
            client,
            email="statistics-owner@example.com",
            display_name="Statistics owner",
        )
        other_headers = register_and_login(
            client,
            email="statistics-other@example.com",
            display_name="Statistics other",
        )

        create_daily_log(
            client,
            headers=owner_headers,
            date="2026-09-30",
            steps=12000,
        )
        create_run(
            client,
            headers=owner_headers,
            date="2026-09-30",
            distance_km=10,
            duration_seconds=3600,
        )
        create_body_metric(
            client,
            headers=owner_headers,
            date="2026-09-30",
            weight_kg=90,
        )

        owner_session = create_workout_session(
            client,
            headers=owner_headers,
            date="2026-09-30",
        )
        owner_exercise = create_workout_exercise(
            client,
            headers=owner_headers,
            session_id=owner_session["id"],
        )
        create_workout_set(
            client,
            headers=owner_headers,
            exercise_id=owner_exercise["id"],
            repetitions=10,
            weight_kg=100,
        )

        response = client.get(
            "/statistics/summary",
            headers=other_headers,
            params={
                "start_date": "2026-09-30",
                "end_date": "2026-09-30",
            },
        )

    assert response.status_code == 200
    assert response.json()["steps"]["total"] == 0
    assert response.json()["workouts"]["sessions"] == 0
    assert response.json()["workouts"]["working_sets"] == 0
    assert response.json()["running"]["runs"] == 0
    assert response.json()["body_metrics"]["records"] == 0