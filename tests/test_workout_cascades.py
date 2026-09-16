from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_session(
    client: TestClient,
    *,
    headers: dict[str, str],
) -> int:
    response = client.post(
        "/workout-sessions/",
        headers=headers,
        json={
            "date": "2026-08-01",
            "name": "Sesión de prueba",
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_exercise(
    client: TestClient,
    *,
    headers: dict[str, str],
    session_id: int,
) -> int:
    response = client.post(
        f"/workout-sessions/{session_id}/exercises/",
        headers=headers,
        json={
            "name": "Press banca",
            "muscle_group": "Pectoral",
            "position": 1,
            "technique_notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_set(
    client: TestClient,
    *,
    headers: dict[str, str],
    exercise_id: int,
) -> int:
    response = client.post(
        f"/workout-exercises/{exercise_id}/sets/",
        headers=headers,
        json={
            "set_type": "working",
            "position": 1,
            "target_rep_range": "8-12",
            "repetitions": 10,
            "weight_kg": 60,
            "rir": 2,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_deleting_session_cascades_to_exercises_and_sets():
    with TestClient(app) as client:
        headers = register_and_login(client)

        session_id = create_session(client, headers=headers)
        exercise_id = create_exercise(
            client,
            headers=headers,
            session_id=session_id,
        )
        set_id = create_set(
            client,
            headers=headers,
            exercise_id=exercise_id,
        )

        delete_response = client.delete(
            f"/workout-sessions/{session_id}",
            headers=headers,
        )
        exercise_response = client.get(
            f"/workout-exercises/{exercise_id}",
            headers=headers,
        )
        set_response = client.get(
            f"/workout-sets/{set_id}",
            headers=headers,
        )

    assert delete_response.status_code == 204
    assert exercise_response.status_code == 404
    assert set_response.status_code == 404


def test_deleting_exercise_cascades_to_sets():
    with TestClient(app) as client:
        headers = register_and_login(client)

        session_id = create_session(client, headers=headers)
        exercise_id = create_exercise(
            client,
            headers=headers,
            session_id=session_id,
        )
        set_id = create_set(
            client,
            headers=headers,
            exercise_id=exercise_id,
        )

        delete_response = client.delete(
            f"/workout-exercises/{exercise_id}",
            headers=headers,
        )
        exercise_response = client.get(
            f"/workout-exercises/{exercise_id}",
            headers=headers,
        )
        set_response = client.get(
            f"/workout-sets/{set_id}",
            headers=headers,
        )
        session_response = client.get(
            f"/workout-sessions/{session_id}",
            headers=headers,
        )

    assert delete_response.status_code == 204
    assert exercise_response.status_code == 404
    assert set_response.status_code == 404
    assert session_response.status_code == 200