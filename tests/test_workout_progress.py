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
    assert first_session["sets"][0]["position"] == 2
    assert first_session["sets"][0]["volume_kg"] == 300
    assert first_session["sets"][1]["position"] == 3
    assert first_session["sets"][1]["volume_kg"] == 240
    assert first_session["working_sets"] == 2
    assert first_session["total_repetitions"] == 18
    assert first_session["max_weight_kg"] == 30
    assert first_session["max_volume_set_kg"] == 300

    second_session = data["sessions"][1]
    assert second_session["date"] == "2026-08-21"
    assert second_session["total_volume_kg"] == 325
    assert second_session["sets"][0]["weight_kg"] == 32.5
    assert second_session["working_sets"] == 1
    assert second_session["total_repetitions"] == 10
    assert second_session["max_weight_kg"] == 32.5
    assert second_session["max_volume_set_kg"] == 325


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

def test_workout_progress_includes_session_strength_summaries():
    with TestClient(app) as client:
        exercise_id = create_exercise(
            client,
            session_date="2026-09-08",
            session_name="Empujes con progreso",
            exercise_name="Press banca con barra",
        )

        create_set(
            client,
            exercise_id,
            set_type="warmup",
            position=1,
            repetitions=15,
            weight_kg=20,
            rir=None,
        )
        create_set(
            client,
            exercise_id,
            set_type="working",
            position=2,
            repetitions=10,
            weight_kg=50,
            rir=2,
        )
        create_set(
            client,
            exercise_id,
            set_type="working",
            position=3,
            repetitions=8,
            weight_kg=60,
            rir=1,
        )
        create_set(
            client,
            exercise_id,
            set_type="working",
            position=4,
            repetitions=6,
            weight_kg=55,
            rir=0,
        )

        response = client.get(
            "/workouts/progress",
            params={
                "exercise_name": "Press banca con barra",
            },
        )

    assert response.status_code == 200

    session = response.json()["sessions"][0]

    assert session["working_sets"] == 3
    assert session["total_repetitions"] == 24
    assert session["total_volume_kg"] == 1310
    assert session["max_weight_kg"] == 60
    assert session["max_volume_set_kg"] == 500

def test_list_exercise_names_with_progress_returns_empty_list():
    with TestClient(app) as client:
        response = client.get("/workouts/exercise-names")

    assert response.status_code == 200
    assert response.json() == []

def test_list_exercise_names_with_progress_returns_unique_sorted_names():
    with TestClient(app) as client:
        first_session_exercise_id = create_exercise(
            client,
            session_date="2026-09-01",
            session_name="Torso A",
            exercise_name="Remo con barra",
        )
        create_set(
            client,
            first_session_exercise_id,
            set_type="working",
            position=1,
            repetitions=10,
            weight_kg=50,
            rir=2,
        )

        repeated_exercise_id = create_exercise(
            client,
            session_date="2026-09-02",
            session_name="Torso B",
            exercise_name="Remo con barra",
        )
        create_set(
            client,
            repeated_exercise_id,
            set_type="working",
            position=1,
            repetitions=8,
            weight_kg=55,
            rir=1,
        )

        press_exercise_id = create_exercise(
            client,
            session_date="2026-09-03",
            session_name="Empujes",
            exercise_name="Press banca con barra",
        )
        create_set(
            client,
            press_exercise_id,
            set_type="working",
            position=1,
            repetitions=10,
            weight_kg=60,
            rir=2,
        )

        warmup_only_exercise_id = create_exercise(
            client,
            session_date="2026-09-04",
            session_name="Pierna",
            exercise_name="Sentadilla",
        )
        create_set(
            client,
            warmup_only_exercise_id,
            set_type="warmup",
            position=1,
            repetitions=12,
            weight_kg=20,
            rir=None,
        )

        response = client.get("/workouts/exercise-names")

    assert response.status_code == 200
    assert response.json() == [
        "Press banca con barra",
        "Remo con barra",
    ]

def test_personal_records_returns_all_metrics_for_working_sets():
    with TestClient(app) as client:
        exercise_name = "Press banca marcas personales"

        first_exercise_id = create_exercise(
            client,
            session_date="2026-09-01",
            session_name="Empujes A",
            exercise_name=exercise_name,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="warmup",
            position=1,
            repetitions=15,
            weight_kg=20,
            rir=None,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="working",
            position=2,
            repetitions=10,
            weight_kg=60,
            rir=2,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="working",
            position=3,
            repetitions=8,
            weight_kg=70,
            rir=1,
        )

        second_exercise_id = create_exercise(
            client,
            session_date="2026-09-08",
            session_name="Empujes B",
            exercise_name=exercise_name,
        )
        create_set(
            client,
            second_exercise_id,
            set_type="working",
            position=1,
            repetitions=12,
            weight_kg=55,
            rir=1,
        )
        create_set(
            client,
            second_exercise_id,
            set_type="working",
            position=2,
            repetitions=5,
            weight_kg=80,
            rir=0,
        )
        create_set(
            client,
            second_exercise_id,
            set_type="drop_set",
            position=3,
            repetitions=20,
            weight_kg=30,
            rir=0,
        )

        response = client.get(
            "/workouts/personal-records",
            params={"exercise_name": exercise_name},
        )

    assert response.status_code == 200

    body = response.json()
    assert len(body) == 1
    assert body[0]["exercise_name"] == exercise_name

    records = {
        record["metric"]: record
        for record in body[0]["records"]
    }

    assert records["max_weight_kg"]["value"] == 80
    assert records["max_weight_kg"]["date"] == "2026-09-08"
    assert records["max_weight_kg"]["repetitions"] == 5
    assert records["max_weight_kg"]["volume_kg"] == 400

    assert records["max_repetitions"]["value"] == 12
    assert records["max_repetitions"]["weight_kg"] == 55

    assert records["max_set_volume_kg"]["value"] == 660
    assert records["max_set_volume_kg"]["repetitions"] == 12
    assert records["max_set_volume_kg"]["weight_kg"] == 55

    assert records["estimated_one_rep_max_kg"]["value"] == 93.33
    assert records["estimated_one_rep_max_kg"]["weight_kg"] == 80
    assert records["estimated_one_rep_max_kg"]["repetitions"] == 5

    assert records["max_session_volume_kg"]["value"] == 1160
    assert records["max_session_volume_kg"]["date"] == "2026-09-01"
    assert records["max_session_volume_kg"]["set_id"] is None
    assert records["max_session_volume_kg"]["repetitions"] is None
    assert records["max_session_volume_kg"]["weight_kg"] is None
    assert records["max_session_volume_kg"]["volume_kg"] == 1160


def test_personal_records_returns_empty_list_without_working_sets():
    with TestClient(app) as client:
        response = client.get("/workouts/personal-records")

    assert response.status_code == 200
    assert response.json() == []


def test_personal_records_filters_by_exercise_name():
    with TestClient(app) as client:
        press_exercise_id = create_exercise(
            client,
            session_date="2026-09-10",
            session_name="Empujes",
            exercise_name="Press de prueba",
        )
        create_set(
            client,
            press_exercise_id,
            set_type="working",
            position=1,
            repetitions=8,
            weight_kg=70,
            rir=2,
        )

        row_exercise_id = create_exercise(
            client,
            session_date="2026-09-10",
            session_name="Tracción",
            exercise_name="Remo de prueba",
        )
        create_set(
            client,
            row_exercise_id,
            set_type="working",
            position=1,
            repetitions=10,
            weight_kg=60,
            rir=2,
        )

        response = client.get(
            "/workouts/personal-records",
            params={"exercise_name": "Press de prueba"},
        )

    assert response.status_code == 200
    assert [record["exercise_name"] for record in response.json()] == [
        "Press de prueba",
    ]


def test_personal_records_returns_404_for_unknown_exercise():
    with TestClient(app) as client:
        response = client.get(
            "/workouts/personal-records",
            params={"exercise_name": "Ejercicio inexistente"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existen series de trabajo para ese ejercicio."
    )


def test_personal_records_rejects_blank_exercise_name():
    with TestClient(app) as client:
        response = client.get(
            "/workouts/personal-records",
            params={"exercise_name": "   "},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "El nombre del ejercicio no puede estar vacío."
    )


def test_personal_records_uses_oldest_set_when_values_tie():
    with TestClient(app) as client:
        exercise_name = "Remo empate"

        first_exercise_id = create_exercise(
            client,
            session_date="2026-09-01",
            session_name="Tracción A",
            exercise_name=exercise_name,
        )
        create_set(
            client,
            first_exercise_id,
            set_type="working",
            position=1,
            repetitions=10,
            weight_kg=60,
            rir=2,
        )

        second_exercise_id = create_exercise(
            client,
            session_date="2026-09-08",
            session_name="Tracción B",
            exercise_name=exercise_name,
        )
        create_set(
            client,
            second_exercise_id,
            set_type="working",
            position=1,
            repetitions=10,
            weight_kg=60,
            rir=2,
        )

        response = client.get(
            "/workouts/personal-records",
            params={"exercise_name": exercise_name},
        )

    assert response.status_code == 200

    records = {
        record["metric"]: record
        for record in response.json()[0]["records"]
    }

    assert records["max_weight_kg"]["date"] == "2026-09-01"
    assert records["max_repetitions"]["date"] == "2026-09-01"
    assert records["max_set_volume_kg"]["date"] == "2026-09-01"
    assert records["estimated_one_rep_max_kg"]["date"] == "2026-09-01"
    assert records["max_session_volume_kg"]["date"] == "2026-09-01"