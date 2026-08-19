from fastapi.testclient import TestClient

from app.main import app


def test_create_workout_session():
    with TestClient(app) as client:
        response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-14",
                "name": "Empujes",
                "notes": "Sesión inicial de empujes.",
            },
        )

    assert response.status_code == 201
    assert response.json()["date"] == "2026-08-14"
    assert response.json()["name"] == "Empujes"
    assert response.json()["notes"] == "Sesión inicial de empujes."


def test_list_workout_sessions():
    with TestClient(app) as client:
        create_response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-15",
                "name": "Tirón",
                "notes": None,
            },
        )

        assert create_response.status_code == 201

        response = client.get("/workout-sessions/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(
        session["id"] == create_response.json()["id"]
        for session in response.json()
    )


def test_get_workout_session():
    with TestClient(app) as client:
        create_response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-16",
                "name": "Pierna",
                "notes": None,
            },
        )

        assert create_response.status_code == 201

        session_id = create_response.json()["id"]
        response = client.get(f"/workout-sessions/{session_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Pierna"


def test_delete_workout_session():
    with TestClient(app) as client:
        create_response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-17",
                "name": "Movilidad",
                "notes": None,
            },
        )

        assert create_response.status_code == 201

        session_id = create_response.json()["id"]

        delete_response = client.delete(f"/workout-sessions/{session_id}")
        get_response = client.get(f"/workout-sessions/{session_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_empty_workout_name_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-18",
                "name": "",
                "notes": None,
            },
        )

    assert response.status_code == 422

def test_repeat_workout_session_copies_exercises_without_sets():
    with TestClient(app) as client:
        session_response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-14",
                "name": "Empujes",
                "notes": "Sesión de referencia.",
            },
        )
        assert session_response.status_code == 201

        original_session_id = session_response.json()["id"]

        first_exercise_response = client.post(
            f"/workout-sessions/{original_session_id}/exercises/",
            json={
                "name": "Press inclinado con mancuernas",
                "muscle_group": "Pectoral",
                "position": 1,
                "technique_notes": "Mantener los hombros atrás.",
            },
        )
        assert first_exercise_response.status_code == 201

        second_exercise_response = client.post(
            f"/workout-sessions/{original_session_id}/exercises/",
            json={
                "name": "Elevación lateral con mancuerna",
                "muscle_group": "Deltoides lateral",
                "position": 2,
                "technique_notes": None,
            },
        )
        assert second_exercise_response.status_code == 201

        set_response = client.post(
            f"/workout-exercises/{first_exercise_response.json()['id']}/sets/",
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
        assert set_response.status_code == 201

        repeat_response = client.post(
            f"/workout-sessions/{original_session_id}/repeat",
        )

        assert repeat_response.status_code == 201, repeat_response.json()

        repeated_session = repeat_response.json()
        repeated_session_id = repeated_session["id"]

        repeated_exercises_response = client.get(
            f"/workout-sessions/{repeated_session_id}/exercises/",
        )
        assert repeated_exercises_response.status_code == 200

        repeated_exercises = repeated_exercises_response.json()

        copied_sets_response = client.get(
            f"/workout-exercises/{repeated_exercises[0]['id']}/sets/",
        )

    assert repeated_session_id != original_session_id
    assert repeated_session["name"] == "Empujes"
    assert repeated_session["notes"] == "Sesión de referencia."
    assert len(repeated_exercises) == 2

    assert repeated_exercises[0]["name"] == "Press inclinado con mancuernas"
    assert repeated_exercises[0]["muscle_group"] == "Pectoral"
    assert repeated_exercises[0]["position"] == 1
    assert repeated_exercises[0]["technique_notes"] == "Mantener los hombros atrás."

    assert repeated_exercises[1]["name"] == "Elevación lateral con mancuerna"
    assert repeated_exercises[1]["muscle_group"] == "Deltoides lateral"
    assert repeated_exercises[1]["position"] == 2

    assert copied_sets_response.status_code == 200
    assert copied_sets_response.json() == []

def test_repeat_missing_workout_session_returns_not_found():
    with TestClient(app) as client:
        response = client.post("/workout-sessions/999999/repeat")

    assert response.status_code == 404

def test_update_workout_session():
    with TestClient(app) as client:
        create_response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-10",
                "name": "Rutina original",
                "notes": "Notas originales.",
            },
        )
        assert create_response.status_code == 201

        session_id = create_response.json()["id"]

        response = client.put(
            f"/workout-sessions/{session_id}",
            json={
                "date": "2026-08-11",
                "name": "Rutina actualizada",
                "notes": "Notas actualizadas.",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": session_id,
        "date": "2026-08-11",
        "name": "Rutina actualizada",
        "notes": "Notas actualizadas.",
    }


def test_update_missing_workout_session_returns_not_found():
    with TestClient(app) as client:
        response = client.put(
            "/workout-sessions/999999",
            json={
                "date": "2026-08-11",
                "name": "No existe",
                "notes": None,
            },
        )

    assert response.status_code == 404