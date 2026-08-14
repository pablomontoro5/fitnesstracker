from fastapi.testclient import TestClient

from app.main import app


def create_exercise(
    client: TestClient,
    *,
    session_date: str,
    session_name: str,
    exercise_name: str,
) -> int:
    session_response = client.post(
        "/workout-sessions/",
        json={
            "date": session_date,
            "name": session_name,
            "notes": None,
        },
    )
    assert session_response.status_code == 201

    session_id = session_response.json()["id"]

    exercise_response = client.post(
        f"/workout-sessions/{session_id}/exercises/",
        json={
            "name": exercise_name,
            "muscle_group": "Pectoral",
            "position": 1,
            "technique_notes": None,
        },
    )
    assert exercise_response.status_code == 201

    return exercise_response.json()["id"]


def create_set(
    client: TestClient,
    exercise_id: int,
    *,
    set_type: str,
    position: int,
    repetitions: int,
    weight_kg: float,
    rir: float | None,
) -> None:
    response = client.post(
        f"/workout-exercises/{exercise_id}/sets/",
        json={
            "set_type": set_type,
            "position": position,
            "target_rep_range": "8-12",
            "repetitions": repetitions,
            "weight_kg": weight_kg,
            "rir": rir,
            "notes": None,
        },
    )
    assert response.status_code == 201


def test_workout_progress_returns_working_sets_grouped_by_session():
    with TestClient(app) as client:
        exercise_name = "Press inclinado con mancuernas"

        first_exercise_id = create_exercise(
            client,
            session_date="2026-08-14",
            session_name="Empujes A",
            exercise_name=exercise_name,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="warmup",
            position=1,
            repetitions=15,
            weight_kg=10,
            rir=None,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="working",
            position=2,
            repetitions=10,
            weight_kg=30,
            rir=2,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="working",
            position=3,
            repetitions=8,
            weight_kg=30,
            rir=1,
        )

        second_exercise_id = create_exercise(
            client,
            session_date="2026-08-21",
            session_name="Empujes B",
            exercise_name=exercise_name,
        )
        create_set(
            client,
            second_exercise_id,
            set_type="working",
            position=1,
            repetitions=10,
            weight_kg=32.5,
            rir=1,
        )

        response = client.get(
            "/workouts/progress",
            params={"exercise_name": exercise_name},
        )

    assert response.status_code == 200

    data = response.json()
    assert data["exercise_name"] == exercise_name
    assert len(data["sessions"]) == 2

    first_session = data["sessions"][0]
    assert first_session["date"] == "2026-08-14"
    assert first_session["session_name"] == "Empujes A"
    assert first_session["total_volume_kg"] == 540
    assert len(first_session["sets"]) == 2
    assert first_session["sets"][0]["volume_kg"] == 300
    assert first_session["sets"][1]["volume_kg"] == 240

    second_session = data["sessions"][1]
    assert second_session["date"] == "2026-08-21"
    assert second_session["total_volume_kg"] == 325
    assert second_session["sets"][0]["weight_kg"] == 32.5


def test_workout_progress_returns_404_when_exercise_has_no_working_sets():
    with TestClient(app) as client:
        exercise_id = create_exercise(
            client,
            session_date="2026-08-14",
            session_name="Empujes sin trabajo",
            exercise_name="Aperturas en pec deck",
        )
        create_set(
            client,
            exercise_id,
            set_type="warmup",
            position=1,
            repetitions=15,
            weight_kg=10,
            rir=None,
        )

        response = client.get(
            "/workouts/progress",
            params={"exercise_name": "Aperturas en pec deck"},
        )

    assert response.status_code == 404

def test_workout_progress_requires_exercise_name():
    with TestClient(app) as client:
        response = client.get("/workouts/progress")

    assert response.status_code == 422