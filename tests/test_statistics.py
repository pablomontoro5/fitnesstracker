from fastapi.testclient import TestClient

from app.main import app

import pytest

from app.db import get_connection


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
    date: str,
    steps: int,
) -> dict:
    response = client.post(
        "/daily-logs/",
        json={
            "date": date,
            "steps": steps,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_workout_session(
    client: TestClient,
    *,
    date: str,
    name: str = "Torso",
) -> dict:
    response = client.post(
        "/workout-sessions/",
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
    )

    assert response.status_code == 201
    return response.json()


def create_workout_set(
    client: TestClient,
    *,
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
    )

    assert response.status_code == 201
    return response.json()


def create_run(
    client: TestClient,
    *,
    date: str,
    distance_km: float,
    duration_seconds: int,
) -> dict:
    response = client.post(
        "/runs/",
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
    )

    assert response.status_code == 201
    return response.json()


def get_summary(
    client: TestClient,
    *,
    start_date: str = "2026-09-30",
    end_date: str = "2026-10-01",
) -> dict:
    response = client.get(
        "/statistics/summary",
        params={
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    assert response.status_code == 200
    return response.json()


def test_statistics_summary_is_empty_when_no_data_exists():
    with TestClient(app) as client:
        summary = get_summary(client)

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
        create_daily_log(
            client,
            date="2026-09-30",
            steps=8000,
        )
        create_daily_log(
            client,
            date="2026-10-01",
            steps=12000,
        )

        session = create_workout_session(
            client,
            date="2026-09-30",
        )
        exercise = create_workout_exercise(
            client,
            session_id=session["id"],
        )

        create_workout_set(
            client,
            exercise_id=exercise["id"],
            position=1,
            repetitions=10,
            weight_kg=50,
        )
        create_workout_set(
            client,
            exercise_id=exercise["id"],
            position=2,
            repetitions=8,
            weight_kg=60,
        )

        create_run(
            client,
            date="2026-09-30",
            distance_km=5,
            duration_seconds=1500,
        )
        create_run(
            client,
            date="2026-10-01",
            distance_km=10,
            duration_seconds=3600,
        )

        create_body_metric(
            client,
            date="2026-09-30",
            weight_kg=80,
        )
        create_body_metric(
            client,
            date="2026-10-01",
            weight_kg=79.5,
        )

        summary = get_summary(client)

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
        create_daily_log(
            client,
            date="2026-09-29",
            steps=9999,
        )
        create_daily_log(
            client,
            date="2026-10-01",
            steps=1000,
        )
        create_daily_log(
            client,
            date="2026-11-01",
            steps=8888,
        )

        create_run(
            client,
            date="2026-09-29",
            distance_km=50,
            duration_seconds=15000,
        )
        create_run(
            client,
            date="2026-10-01",
            distance_km=5,
            duration_seconds=1500,
        )

        summary = get_summary(client)

    assert summary["steps"]["total"] == 1000
    assert summary["steps"]["days_logged"] == 1
    assert summary["running"]["runs"] == 1
    assert summary["running"]["distance_km"] == 5
    assert summary["running"]["duration_seconds"] == 1500
    assert summary["running"]["average_pace_seconds_km"] == 300


def test_statistics_summary_only_counts_working_sets():
    with TestClient(app) as client:
        session = create_workout_session(
            client,
            date="2026-09-30",
        )
        exercise = create_workout_exercise(
            client,
            session_id=session["id"],
        )

        create_workout_set(
            client,
            exercise_id=exercise["id"],
            set_type="warmup",
            position=1,
            repetitions=15,
            weight_kg=20,
        )
        create_workout_set(
            client,
            exercise_id=exercise["id"],
            set_type="approximation",
            position=2,
            repetitions=8,
            weight_kg=40,
        )
        create_workout_set(
            client,
            exercise_id=exercise["id"],
            set_type="working",
            position=3,
            repetitions=10,
            weight_kg=50,
        )
        create_workout_set(
            client,
            exercise_id=exercise["id"],
            set_type="drop_set",
            position=4,
            repetitions=12,
            weight_kg=30,
        )

        summary = get_summary(client)

    assert summary["workouts"]["sessions"] == 1
    assert summary["workouts"]["exercises"] == 1
    assert summary["workouts"]["working_sets"] == 1
    assert summary["workouts"]["repetitions"] == 10
    assert summary["workouts"]["volume_kg"] == 500


def test_statistics_summary_rejects_inverted_date_range():
    with TestClient(app) as client:
        response = client.get(
            "/statistics/summary",
            params={
                "start_date": "2026-10-01",
                "end_date": "2026-09-30",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "start_date no puede ser posterior a end_date."
    )

def test_statistics_summary_rejects_invalid_date():
    with TestClient(app) as client:
        response = client.get(
            "/statistics/summary",
            params={
                "start_date": "not-a-date",
                "end_date": "2026-10-01",
            },
        )

    assert response.status_code == 422