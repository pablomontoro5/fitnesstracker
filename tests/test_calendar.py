from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login

def create_planned_workout(
    client: TestClient,
    *,
    headers: dict[str, str],
    scheduled_date: str,
    name: str,
) -> dict:
    response = client.post(
        "/planned-workouts/",
        headers=headers,
        json={
            "scheduled_date": scheduled_date,
            "name": name,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()
def create_workout_session(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    name: str,
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

    assert response.status_code == 201, response.text
    return response.json()
def create_run(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    distance_km: float,
    duration_seconds: int = 1800,
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
def test_calendar_combines_activity_for_a_day():
    with TestClient(app) as client:
        headers = register_and_login(client)

        daily_log_response = client.post(
            "/daily-logs/",
            headers=headers,
            json={
                "date": "2026-09-21",
                "steps": 8500,
                "notes": None,
            },
        )
        assert daily_log_response.status_code == 201

        recovery_response = client.post(
            "/recovery-logs/",
            headers=headers,
            json={
                "date": "2026-09-21",
                "sleep_minutes": 450,
                "sleep_quality": 4,
                "is_rest_day": False,
                "notes": None,
            },
        )
        assert recovery_response.status_code == 201

        create_workout_session(
            client,
            headers=headers,
            date="2026-09-21",
            name="Torso A",
        )
        create_run(
            client,
            headers=headers,
            date="2026-09-21",
            distance_km=5.5,
        )
        planned_workout = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-21",
            name="Torso A",
        )

        response = client.get(
            "/calendar/activity",
            headers=headers,
            params={
                "start_date": "2026-09-21",
                "end_date": "2026-09-21",
            },
        )

    assert response.status_code == 200
    assert response.json()["days"] == [
        {
            "date": "2026-09-21",
            "steps": 8500,
            "has_workout": True,
            "workout_sessions": 1,
            "running_distance_km": 5.5,
            "sleep_minutes": 450,
            "is_rest_day": False,
            "planned_workouts": [
                {
                    "id": planned_workout["id"],
                    "name": "Torso A",
                    "status": "planned",
                }
            ],
        }
    ]
def test_calendar_aggregates_workouts_and_runs_for_the_same_day():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_workout_session(
            client,
            headers=headers,
            date="2026-09-22",
            name="Torso A",
        )
        create_workout_session(
            client,
            headers=headers,
            date="2026-09-22",
            name="Pierna A",
        )

        create_run(
            client,
            headers=headers,
            date="2026-09-22",
            distance_km=3.2,
        )
        create_run(
            client,
            headers=headers,
            date="2026-09-22",
            distance_km=4.8,
        )

        response = client.get(
            "/calendar/activity",
            headers=headers,
            params={
                "start_date": "2026-09-22",
                "end_date": "2026-09-22",
            },
        )

    assert response.status_code == 200
    day = response.json()["days"][0]
    assert day["has_workout"] is True
    assert day["workout_sessions"] == 2
    assert day["running_distance_km"] == 8.0
def test_calendar_returns_multiple_planned_workouts_in_creation_order():
    with TestClient(app) as client:
        headers = register_and_login(client)

        first = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-23",
            name="Movilidad",
        )
        second = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-23",
            name="Torso A",
        )

        response = client.get(
            "/calendar/activity",
            headers=headers,
            params={
                "start_date": "2026-09-23",
                "end_date": "2026-09-23",
            },
        )

    assert response.status_code == 200
    assert response.json()["days"][0]["planned_workouts"] == [
        {
            "id": first["id"],
            "name": "Movilidad",
            "status": "planned",
        },
        {
            "id": second["id"],
            "name": "Torso A",
            "status": "planned",
        },
    ]
def test_calendar_isolated_between_users():
    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana-calendar@example.com",
            display_name="Ana Calendar",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno-calendar@example.com",
            display_name="Bruno Calendar",
        )

        daily_log_response = client.post(
            "/daily-logs/",
            headers=ana_headers,
            json={
                "date": "2026-09-24",
                "steps": 9000,
                "notes": None,
            },
        )
        assert daily_log_response.status_code == 201

        create_workout_session(
            client,
            headers=ana_headers,
            date="2026-09-24",
            name="Torso de Ana",
        )
        create_run(
            client,
            headers=ana_headers,
            date="2026-09-24",
            distance_km=7.0,
        )
        create_planned_workout(
            client,
            headers=ana_headers,
            scheduled_date="2026-09-24",
            name="Plan de Ana",
        )

        response = client.get(
            "/calendar/activity",
            headers=bruno_headers,
            params={
                "start_date": "2026-09-24",
                "end_date": "2026-09-24",
            },
        )

    assert response.status_code == 200
    assert response.json()["days"] == [
        {
            "date": "2026-09-24",
            "steps": 0,
            "has_workout": False,
            "workout_sessions": 0,
            "running_distance_km": 0.0,
            "sleep_minutes": None,
            "is_rest_day": False,
            "planned_workouts": [],
        }
    ]
def test_calendar_rejects_inverted_date_range():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.get(
            "/calendar/activity",
            headers=headers,
            params={
                "start_date": "2026-09-24",
                "end_date": "2026-09-21",
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "start_date no puede ser posterior a end_date."
    }
def test_calendar_rejects_range_over_366_days():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.get(
            "/calendar/activity",
            headers=headers,
            params={
                "start_date": "2025-01-01",
                "end_date": "2026-01-02",
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "El intervalo del calendario no puede superar "
            "366 días."
        )
    }
def test_calendar_requires_authentication():
    with TestClient(app) as client:
        response = client.get(
            "/calendar/activity",
            params={
                "start_date": "2026-09-21",
                "end_date": "2026-09-21",
            },
        )

    assert response.status_code == 401

def test_calendar_returns_every_day_in_requested_range():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.get(
            "/calendar/activity",
            headers=headers,
            params={
                "start_date": "2026-09-21",
                "end_date": "2026-09-23",
            },
        )

    assert response.status_code == 200

    payload = response.json()
    assert payload["start_date"] == "2026-09-21"
    assert payload["end_date"] == "2026-09-23"
    assert [day["date"] for day in payload["days"]] == [
        "2026-09-21",
        "2026-09-22",
        "2026-09-23",
    ]

    assert payload["days"] == [
        {
            "date": "2026-09-21",
            "steps": 0,
            "has_workout": False,
            "workout_sessions": 0,
            "running_distance_km": 0.0,
            "sleep_minutes": None,
            "is_rest_day": False,
            "planned_workouts": [],
        },
        {
            "date": "2026-09-22",
            "steps": 0,
            "has_workout": False,
            "workout_sessions": 0,
            "running_distance_km": 0.0,
            "sleep_minutes": None,
            "is_rest_day": False,
            "planned_workouts": [],
        },
        {
            "date": "2026-09-23",
            "steps": 0,
            "has_workout": False,
            "workout_sessions": 0,
            "running_distance_km": 0.0,
            "sleep_minutes": None,
            "is_rest_day": False,
            "planned_workouts": [],
        },
    ]