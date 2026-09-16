from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_exercise(
    client: TestClient,
    *,
    headers: dict[str, str],
) -> int:
    session_response = client.post(
        "/workout-sessions/",
        headers=headers,
        json={
            "date": "2026-08-14",
            "name": "Empujes para series",
            "notes": None,
        },
    )
    assert session_response.status_code == 201

    session_id = session_response.json()["id"]

    exercise_response = client.post(
        f"/workout-sessions/{session_id}/exercises/",
        headers=headers,
        json={
            "name": "Press inclinado con mancuernas",
            "muscle_group": "Pectoral",
            "position": 1,
            "technique_notes": None,
        },
    )
    assert exercise_response.status_code == 201

    return exercise_response.json()["id"]


def create_set(
    client: TestClient,
    *,
    headers: dict[str, str],
    exercise_id: int,
    set_type: str = "working",
    position: int = 1,
    target_rep_range: str | None = "8-12",
    repetitions: int = 10,
    weight_kg: float = 30,
    rir: float | None = 2,
    notes: str | None = None,
) -> dict:
    response = client.post(
        f"/workout-exercises/{exercise_id}/sets/",
        headers=headers,
        json={
            "set_type": set_type,
            "position": position,
            "target_rep_range": target_rep_range,
            "repetitions": repetitions,
            "weight_kg": weight_kg,
            "rir": rir,
            "notes": notes,
        },
    )

    assert response.status_code == 201, response.json()
    return response.json()


def test_create_workout_set_calculates_volume():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 10,
                "weight_kg": 30,
                "rir": 2,
                "notes": "Controlar la bajada.",
            },
        )

    assert response.status_code == 201
    assert response.json()["workout_exercise_id"] == exercise_id
    assert response.json()["set_type"] == "working"
    assert response.json()["volume_kg"] == 300


def test_list_workout_sets_orders_by_position():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        create_set(
            client,
            headers=headers,
            exercise_id=exercise_id,
            set_type="working",
            position=2,
            repetitions=8,
            weight_kg=30,
            rir=1,
        )
        create_set(
            client,
            headers=headers,
            exercise_id=exercise_id,
            set_type="warmup",
            position=1,
            target_rep_range=None,
            repetitions=15,
            weight_kg=10,
            rir=None,
        )

        response = client.get(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
        )

    assert response.status_code == 200, response.json()

    sets = response.json()
    assert len(sets) == 2
    assert sets[0]["position"] == 1
    assert sets[0]["set_type"] == "warmup"
    assert sets[1]["position"] == 2
    assert sets[1]["set_type"] == "working"


def test_set_requires_existing_exercise():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/workout-exercises/999999/sets/",
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 10,
                "weight_kg": 30,
                "rir": 2,
                "notes": None,
            },
        )

    assert response.status_code == 404


def test_duplicate_set_position_returns_conflict():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        payload = {
            "set_type": "working",
            "position": 1,
            "target_rep_range": "8-12",
            "repetitions": 10,
            "weight_kg": 30,
            "rir": 2,
            "notes": None,
        }

        first_response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json=payload,
        )
        second_response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                **payload,
                "repetitions": 8,
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_delete_workout_set():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        created_set = create_set(
            client,
            headers=headers,
            exercise_id=exercise_id,
            set_type="approximation",
            target_rep_range=None,
            repetitions=10,
            weight_kg=20,
            rir=None,
        )

        delete_response = client.delete(
            f"/workout-sets/{created_set['id']}",
            headers=headers,
        )
        get_response = client.get(
            f"/workout-sets/{created_set['id']}",
            headers=headers,
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_invalid_set_type_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "invalid",
                "position": 1,
                "target_rep_range": None,
                "repetitions": 10,
                "weight_kg": 30,
                "rir": 2,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_negative_rir_is_accepted():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        existing_sets_response = client.get(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
        )
        assert existing_sets_response.status_code == 200
        assert existing_sets_response.json() == []

        response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "working",
                "position": 10,
                "target_rep_range": "8-12",
                "repetitions": 8,
                "weight_kg": 30,
                "rir": -1,
                "notes": (
                    "Fallo concéntrico con una repetición parcial."
                ),
            },
        )

    assert response.status_code == 201, response.json()
    assert response.json()["rir"] == -1


def test_rir_below_negative_three_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "drop_set",
                "position": 1,
                "target_rep_range": None,
                "repetitions": 8,
                "weight_kg": 20,
                "rir": -3.5,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_zero_repetitions_are_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 0,
                "weight_kg": 30,
                "rir": 2,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_negative_weight_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 10,
                "weight_kg": -1,
                "rir": 2,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_update_workout_set():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        created_set = create_set(
            client,
            headers=headers,
            exercise_id=exercise_id,
        )

        response = client.put(
            f"/workout-sets/{created_set['id']}",
            headers=headers,
            json={
                "set_type": "drop_set",
                "position": 2,
                "target_rep_range": "10-15",
                "repetitions": 12,
                "weight_kg": 25,
                "rir": -1,
                "notes": "Reducir carga al llegar al fallo.",
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == created_set["id"]
    assert response.json()["set_type"] == "drop_set"
    assert response.json()["position"] == 2
    assert response.json()["target_rep_range"] == "10-15"
    assert response.json()["repetitions"] == 12
    assert response.json()["weight_kg"] == 25
    assert response.json()["rir"] == -1
    assert response.json()["notes"] == "Reducir carga al llegar al fallo."
    assert response.json()["volume_kg"] == 300


def test_update_missing_workout_set_returns_not_found():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.put(
            "/workout-sets/999999",
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 10,
                "weight_kg": 30,
                "rir": 2,
                "notes": None,
            },
        )

    assert response.status_code == 404


def test_update_workout_set_rejects_duplicate_position():
    with TestClient(app) as client:
        headers = register_and_login(client)
        exercise_id = create_exercise(client, headers=headers)

        first_response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "warmup",
                "position": 1,
                "target_rep_range": None,
                "repetitions": 15,
                "weight_kg": 10,
                "rir": None,
                "notes": None,
            },
        )
        second_response = client.post(
            f"/workout-exercises/{exercise_id}/sets/",
            headers=headers,
            json={
                "set_type": "working",
                "position": 2,
                "target_rep_range": "8-12",
                "repetitions": 10,
                "weight_kg": 30,
                "rir": 2,
                "notes": None,
            },
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 201

        second_set_id = second_response.json()["id"]

        response = client.put(
            f"/workout-sets/{second_set_id}",
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 10,
                "weight_kg": 30,
                "rir": 2,
                "notes": None,
            },
        )

    assert response.status_code == 409