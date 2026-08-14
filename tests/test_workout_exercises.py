from fastapi.testclient import TestClient

from app.main import app


def create_session(client: TestClient, name: str = "Empujes") -> int:
    response = client.post(
        "/workout-sessions/",
        json={
            "date": "2026-08-14",
            "name": name,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_create_workout_exercise():
    with TestClient(app) as client:
        session_id = create_session(client)

        response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Press inclinado con mancuernas",
                "muscle_group": "Pectoral",
                "position": 1,
                "technique_notes": "Mantener hombros atrás.",
            },
        )

    assert response.status_code == 201
    assert response.json()["workout_session_id"] == session_id
    assert response.json()["name"] == "Press inclinado con mancuernas"
    assert response.json()["position"] == 1


def test_list_workout_exercises_orders_by_position():
    with TestClient(app) as client:
        session_id = create_session(client, name="Empujes ordenados")

        client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Aperturas en pec deck",
                "muscle_group": "Pectoral",
                "position": 2,
                "technique_notes": None,
            },
        )

        client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Press banca en máquina",
                "muscle_group": "Pectoral",
                "position": 1,
                "technique_notes": None,
            },
        )

        response = client.get(
            f"/workout-sessions/{session_id}/exercises/"
        )

    assert response.status_code == 200
    assert response.json()[0]["position"] == 1
    assert response.json()[1]["position"] == 2


def test_exercise_requires_existing_session():
    with TestClient(app) as client:
        response = client.post(
            "/workout-sessions/999999/exercises/",
            json={
                "name": "Elevación lateral con mancuerna",
                "muscle_group": "Deltoides lateral",
                "position": 1,
                "technique_notes": None,
            },
        )

    assert response.status_code == 404


def test_duplicate_exercise_position_returns_conflict():
    with TestClient(app) as client:
        session_id = create_session(client, name="Empujes duplicados")

        payload = {
            "name": "Press inclinado con mancuernas",
            "muscle_group": "Pectoral",
            "position": 1,
            "technique_notes": None,
        }

        first_response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json=payload,
        )

        second_response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                **payload,
                "name": "Press banca en máquina",
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_delete_workout_exercise():
    with TestClient(app) as client:
        session_id = create_session(client, name="Empujes borrar")

        create_response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Elevación lateral en máquina",
                "muscle_group": "Deltoides lateral",
                "position": 1,
                "technique_notes": None,
            },
        )

        exercise_id = create_response.json()["id"]

        delete_response = client.delete(
            f"/workout-exercises/{exercise_id}"
        )
        get_response = client.get(
            f"/workout-exercises/{exercise_id}"
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404

def test_update_workout_exercise():
    with TestClient(app) as client:
        session_id = create_session(client, name="Empujes editar")

        create_response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Press inclinado",
                "muscle_group": "Pectoral",
                "position": 1,
                "technique_notes": None,
            },
        )
        assert create_response.status_code == 201

        exercise_id = create_response.json()["id"]

        response = client.put(
            f"/workout-exercises/{exercise_id}",
            json={
                "name": "Press inclinado con mancuernas",
                "muscle_group": "Pectoral superior",
                "position": 2,
                "technique_notes": "Mantener los hombros atrás y pegados al banco.",
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == exercise_id
    assert response.json()["name"] == "Press inclinado con mancuernas"
    assert response.json()["muscle_group"] == "Pectoral superior"
    assert response.json()["position"] == 2
    assert (
        response.json()["technique_notes"]
        == "Mantener los hombros atrás y pegados al banco."
    )


def test_update_workout_exercise_rejects_duplicate_position():
    with TestClient(app) as client:
        session_id = create_session(client, name="Empujes editar posición")

        first_response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Press banca",
                "muscle_group": "Pectoral",
                "position": 1,
                "technique_notes": None,
            },
        )
        assert first_response.status_code == 201

        second_response = client.post(
            f"/workout-sessions/{session_id}/exercises/",
            json={
                "name": "Aperturas",
                "muscle_group": "Pectoral",
                "position": 2,
                "technique_notes": None,
            },
        )
        assert second_response.status_code == 201

        second_exercise_id = second_response.json()["id"]

        response = client.put(
            f"/workout-exercises/{second_exercise_id}",
            json={
                "name": "Aperturas",
                "muscle_group": "Pectoral",
                "position": 1,
                "technique_notes": None,
            },
        )

    assert response.status_code == 409