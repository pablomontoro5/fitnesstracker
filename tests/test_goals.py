from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.routers.goals import build_goals_progress


def test_create_or_update_daily_steps_goal():
    with TestClient(app) as client:
        response = client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )

        list_response = client.get("/goals/")

    assert response.status_code == 200

    goal = response.json()

    assert goal["goal_type"] == "daily_steps"
    assert goal["target_value"] == 8000

    assert list_response.status_code == 200
    assert list_response.json() == [goal]


def test_updating_goal_does_not_create_duplicate():
    with TestClient(app) as client:
        first_response = client.put(
            "/goals/weekly_workouts",
            json={
                "target_value": 3,
            },
        )

        second_response = client.put(
            "/goals/weekly_workouts",
            json={
                "target_value": 4,
            },
        )

        list_response = client.get("/goals/")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["id"] == first_response.json()["id"]
    assert second_response.json()["target_value"] == 4
    assert list_response.json() == [second_response.json()]


def test_delete_goal():
    with TestClient(app) as client:
        create_response = client.put(
            "/goals/weekly_running_km",
            json={
                "target_value": 12.5,
            },
        )

        assert create_response.status_code == 200

        delete_response = client.delete("/goals/weekly_running_km")
        list_response = client.get("/goals/")

    assert delete_response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_missing_goal_returns_not_found():
    with TestClient(app) as client:
        response = client.delete("/goals/daily_steps")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe un objetivo de este tipo."
    }


def test_goal_type_must_be_supported():
    with TestClient(app) as client:
        response = client.put(
            "/goals/monthly_steps",
            json={
                "target_value": 100000,
            },
        )

    assert response.status_code == 422


def test_goal_target_value_must_be_positive():
    with TestClient(app) as client:
        response = client.put(
            "/goals/daily_steps",
            json={
                "target_value": 0,
            },
        )

    assert response.status_code == 422


def test_goals_progress_calculates_today_and_current_week():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )
        client.put(
            "/goals/weekly_workouts",
            json={
                "target_value": 3,
            },
        )
        client.put(
            "/goals/weekly_running_km",
            json={
                "target_value": 10,
            },
        )

        client.post(
            "/daily-logs/",
            json={
                "date": "2026-09-09",
                "steps": 6400,
                "notes": None,
            },
        )

        client.post(
            "/workout-sessions/",
            json={
                "date": "2026-09-07",
                "name": "Empujes",
                "notes": None,
            },
        )
        client.post(
            "/workout-sessions/",
            json={
                "date": "2026-09-09",
                "name": "Tirón",
                "notes": None,
            },
        )
        client.post(
            "/workout-sessions/",
            json={
                "date": "2026-09-06",
                "name": "Sesión anterior",
                "notes": None,
            },
        )

        client.post(
            "/runs/",
            json={
                "date": "2026-09-07",
                "distance_km": 4.5,
                "duration_seconds": 1500,
                "notes": None,
            },
        )
        client.post(
            "/runs/",
            json={
                "date": "2026-09-09",
                "distance_km": 3.2,
                "duration_seconds": 1200,
                "notes": None,
            },
        )
        client.post(
            "/runs/",
            json={
                "date": "2026-09-06",
                "distance_km": 10,
                "duration_seconds": 3600,
                "notes": None,
            },
        )

    progress_by_type = {
        progress.goal_type: progress
        for progress in build_goals_progress(today=today)
    }

    steps_progress = progress_by_type["daily_steps"]
    workouts_progress = progress_by_type["weekly_workouts"]
    running_progress = progress_by_type["weekly_running_km"]

    assert steps_progress.current_value == 6400
    assert steps_progress.target_value == 8000
    assert steps_progress.progress_percentage == 80
    assert steps_progress.is_completed is False

    assert workouts_progress.current_value == 2
    assert workouts_progress.target_value == 3
    assert workouts_progress.progress_percentage == 66.7
    assert workouts_progress.is_completed is False

    assert running_progress.current_value == 7.7
    assert running_progress.target_value == 10
    assert running_progress.progress_percentage == 77
    assert running_progress.is_completed is False


def test_goals_progress_caps_percentage_at_one_hundred():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )
        client.post(
            "/daily-logs/",
            json={
                "date": "2026-09-09",
                "steps": 10000,
                "notes": None,
            },
        )

    progress_items = build_goals_progress(today=today)

    assert len(progress_items) == 1

    progress = progress_items[0]

    assert progress.goal_type == "daily_steps"
    assert progress.current_value == 10000
    assert progress.progress_percentage == 100
    assert progress.is_completed is True