from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login

def create_run(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str = "2026-08-19",
    distance_km: float = 5,
    duration_seconds: int = 1500,
    notes: str | None = "Rodaje suave.",
) -> dict:
    response = client.post(
        "/runs/",
        headers=headers,
        json={
            "date": date,
            "distance_km": distance_km,
            "duration_seconds": duration_seconds,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_run_calculates_average_pace():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.post(
            "/runs/",
            headers=headers,
            json={
                "date": "2026-08-19",
                "distance_km": 5,
                "duration_seconds": 1500,
                "notes": "Rodaje suave.",
            },
        )

    assert response.status_code == 201

    run = response.json()

    assert run["date"] == "2026-08-19"
    assert run["distance_km"] == 5
    assert run["duration_seconds"] == 1500
    assert run["average_pace_seconds_km"] == 300
    assert run["notes"] == "Rodaje suave."


def test_list_runs_orders_by_date_descending():
    with TestClient(app) as client:
        headers = register_and_login(client)

        older_run = create_run(
            client,
            headers=headers,
            date="2026-08-17",
            distance_km=5,
            duration_seconds=1500,
        )
        newer_run = create_run(
            client,
            headers=headers,
            date="2026-08-18",
            distance_km=10,
            duration_seconds=3600,
        )

        response = client.get(
            "/runs/",
            headers=headers,
        )

    assert response.status_code == 200

    runs = response.json()
    run_ids = [run["id"] for run in runs]

    assert newer_run["id"] in run_ids
    assert older_run["id"] in run_ids
    assert run_ids.index(newer_run["id"]) < run_ids.index(older_run["id"])
def test_get_run():
    with TestClient(app) as client:
        headers = register_and_login(client)

        created_run = create_run(
            client,
            headers=headers,
        )

        response = client.get(
            f"/runs/{created_run['id']}",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == created_run
def test_update_run_recalculates_average_pace():
    with TestClient(app) as client:
        headers = register_and_login(client)

        created_run = create_run(
            client,
            headers=headers,
            distance_km=5,
            duration_seconds=1500,
        )

        response = client.put(
            f"/runs/{created_run['id']}",
            headers=headers,
            json={
                "date": "2026-08-20",
                "distance_km": 10,
                "duration_seconds": 3300,
                "notes": "Carrera larga.",
            },
        )

    assert response.status_code == 200

    updated_run = response.json()

    assert updated_run["id"] == created_run["id"]
    assert updated_run["date"] == "2026-08-20"
    assert updated_run["distance_km"] == 10
    assert updated_run["duration_seconds"] == 3300
    assert updated_run["average_pace_seconds_km"] == 330
    assert updated_run["notes"] == "Carrera larga."

def test_delete_run():
    with TestClient(app) as client:
        headers = register_and_login(client)

        created_run = create_run(
            client,
            headers=headers,
        )

        delete_response = client.delete(
            f"/runs/{created_run['id']}",
            headers=headers,
        )
        get_response = client.get(
            f"/runs/{created_run['id']}",
            headers=headers,
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404
def test_get_missing_run_returns_not_found():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.get(
            "/runs/999999",
            headers=headers,
        )

    assert response.status_code == 404

def test_update_missing_run_returns_not_found():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.put(
            "/runs/999999",
            headers=headers,
            json={
                "date": "2026-08-20",
                "distance_km": 5,
                "duration_seconds": 1500,
                "notes": None,
            },
        )

    assert response.status_code == 404
def test_delete_missing_run_returns_not_found():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.delete(
            "/runs/999999",
            headers=headers,
        )

    assert response.status_code == 404
def test_zero_distance_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/runs/",
            headers=headers,
            json={
                "date": "2026-08-20",
                "distance_km": 0,
                "duration_seconds": 1500,
                "notes": None,
            },
        )

    assert response.status_code == 422

def test_zero_duration_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/runs/",
            headers=headers,
            json={
                "date": "2026-08-20",
                "distance_km": 5,
                "duration_seconds": 0,
                "notes": None,
            },
        )

    assert response.status_code == 422
def test_users_cannot_access_each_others_runs():
    with TestClient(app) as client:
        owner_headers = register_and_login(
            client,
            email="run-owner@example.com",
            display_name="Run owner",
        )
        other_headers = register_and_login(
            client,
            email="run-other@example.com",
            display_name="Run other",
        )

        owner_run = create_run(
            client,
            headers=owner_headers,
            date="2026-08-21",
        )

        list_response = client.get(
            "/runs/",
            headers=other_headers,
        )
        get_response = client.get(
            f"/runs/{owner_run['id']}",
            headers=other_headers,
        )
        delete_response = client.delete(
            f"/runs/{owner_run['id']}",
            headers=other_headers,
        )

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert get_response.status_code == 404
    assert delete_response.status_code == 404