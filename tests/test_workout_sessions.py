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

def test_update_workout_session():
    with TestClient(app) as client:
        create_response = client.post(
            "/workout-sessions/",
            json={
                "date": "2026-08-14",
                "name": "Empujes",
                "notes": "Sesión inicial.",
            },
        )
        assert create_response.status_code == 201

        session_id = create_response.json()["id"]

        response = client.put(
            f"/workout-sessions/{session_id}",
            json={
                "date": "2026-08-18",
                "name": "Empujes actualizado",
                "notes": "Aumentar la carga en el press inclinado.",
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == session_id
    assert response.json()["date"] == "2026-08-18"
    assert response.json()["name"] == "Empujes actualizado"
    assert response.json()["notes"] == "Aumentar la carga en el press inclinado."

def test_update_missing_workout_session_returns_not_found():
    with TestClient(app) as client:
        response = client.put(
            "/workout-sessions/999999",
            json={
                "date": "2026-08-18",
                "name": "Sesión inexistente",
                "notes": None,
            },
        )

    assert response.status_code == 404