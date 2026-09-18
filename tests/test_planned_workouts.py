from app.db import get_connection, initialize_database
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_template(
    client: TestClient,
    *,
    headers: dict[str, str],
    name: str = "Torso A",
    notes: str | None = "Rutina principal de torso.",
) -> dict:
    response = client.post(
        "/workout-templates/",
        headers=headers,
        json={
            "name": name,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_template_exercise(
    client: TestClient,
    *,
    headers: dict[str, str],
    template_id: int,
    name: str = "Press banca",
    muscle_group: str = "Pectoral",
    position: int = 1,
    technique_notes: str | None = "Escápulas retraídas.",
) -> dict:
    response = client.post(
        f"/workout-templates/{template_id}/exercises/",
        headers=headers,
        json={
            "name": name,
            "muscle_group": muscle_group,
            "position": position,
            "technique_notes": technique_notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_template_set(
    client: TestClient,
    *,
    headers: dict[str, str],
    exercise_id: int,
    set_type: str = "working",
    position: int = 1,
    target_rep_range: str | None = "8-12",
    repetitions: int = 10,
    weight_kg: float = 60.0,
    rir: float | None = 2.0,
    notes: str | None = "Mantener la técnica.",
) -> dict:
    response = client.post(
        f"/workout-templates/exercises/{exercise_id}/sets/",
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

    assert response.status_code == 201
    return response.json()


def create_planned_workout(
    client: TestClient,
    *,
    headers: dict[str, str],
    scheduled_date: str = "2026-09-21",
    workout_template_id: int | None = None,
    name: str | None = "Movilidad y core",
    notes: str | None = "20 minutos de movilidad.",
) -> dict:
    response = client.post(
        "/planned-workouts/",
        headers=headers,
        json={
            "scheduled_date": scheduled_date,
            "workout_template_id": workout_template_id,
            "name": name,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_manual_planned_workout():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/planned-workouts/",
            headers=headers,
            json={
                "scheduled_date": "2026-09-21",
                "name": "Movilidad y core",
                "notes": "20 minutos de movilidad.",
            },
        )

    assert response.status_code == 201

    payload = response.json()
    assert payload["scheduled_date"] == "2026-09-21"
    assert payload["workout_template_id"] is None
    assert payload["name"] == "Movilidad y core"
    assert payload["notes"] == "20 minutos de movilidad."
    assert payload["status"] == "planned"
    assert payload["workout_session_id"] is None


def test_create_planned_workout_from_owned_template():
    with TestClient(app) as client:
        headers = register_and_login(client)
        template = create_template(
            client,
            headers=headers,
            name="Pierna A",
            notes="Sentadilla y peso muerto rumano.",
        )

        planned_workout = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-22",
            workout_template_id=template["id"],
            name=None,
            notes="Entrenar después del trabajo.",
        )

    assert planned_workout["scheduled_date"] == "2026-09-22"
    assert planned_workout["workout_template_id"] == template["id"]
    assert planned_workout["name"] == "Pierna A"
    assert planned_workout["notes"] == "Entrenar después del trabajo."
    assert planned_workout["status"] == "planned"
    assert planned_workout["workout_session_id"] is None


def test_create_planned_workout_requires_template_or_name():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/planned-workouts/",
            headers=headers,
            json={
                "scheduled_date": "2026-09-21",
                "workout_template_id": None,
                "name": None,
                "notes": None,
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "Debes indicar una plantilla o un nombre para "
            "planificar la sesión."
        )
    }


def test_create_planned_workout_rejects_other_users_template():
    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana-planned-template@example.com",
            display_name="Ana Planned Template",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno-planned-template@example.com",
            display_name="Bruno Planned Template",
        )
        ana_template = create_template(
            client,
            headers=ana_headers,
            name="Plantilla de Ana",
        )

        response = client.post(
            "/planned-workouts/",
            headers=bruno_headers,
            json={
                "scheduled_date": "2026-09-21",
                "workout_template_id": ana_template["id"],
                "name": None,
                "notes": None,
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe una plantilla con ese id."
    }


def test_list_planned_workouts_and_filter_by_date_range():
    with TestClient(app) as client:
        headers = register_and_login(client)

        first = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-20",
            name="Movilidad",
        )
        second = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-22",
            name="Torso",
        )
        third = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-25",
            name="Pierna",
        )

        all_response = client.get(
            "/planned-workouts/",
            headers=headers,
        )
        filtered_response = client.get(
            "/planned-workouts/",
            headers=headers,
            params={
                "start_date": "2026-09-21",
                "end_date": "2026-09-24",
            },
        )

    assert all_response.status_code == 200
    assert all_response.json() == [first, second, third]
    assert filtered_response.status_code == 200
    assert filtered_response.json() == [second]


def test_update_planned_workout_and_mark_skipped():
    with TestClient(app) as client:
        headers = register_and_login(client)
        planned_workout = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-21",
            name="Torso A",
            notes="Versión inicial.",
        )

        response = client.put(
            f"/planned-workouts/{planned_workout['id']}",
            headers=headers,
            json={
                "scheduled_date": "2026-09-23",
                "workout_template_id": None,
                "name": "Torso A reprogramado",
                "notes": "Entrenar por la tarde.",
                "status": "skipped",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": planned_workout["id"],
        "scheduled_date": "2026-09-23",
        "workout_template_id": None,
        "name": "Torso A reprogramado",
        "notes": "Entrenar por la tarde.",
        "status": "skipped",
        "workout_session_id": None,
    }


def test_complete_manual_planned_workout_creates_empty_session():
    with TestClient(app) as client:
        headers = register_and_login(client)
        planned_workout = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-21",
            name="Movilidad y core",
            notes="20 minutos de movilidad.",
        )

        response = client.post(
            f"/planned-workouts/{planned_workout['id']}/complete",
            headers=headers,
            json={
                "completed_date": "2026-09-23",
            },
        )

    assert response.status_code == 201
    payload = response.json()

    assert payload["planned_workout"]["status"] == "completed"
    assert payload["planned_workout"]["workout_session_id"] == (
        payload["workout_session"]["id"]
    )
    assert payload["workout_session"] == {
        "id": payload["workout_session"]["id"],
        "date": "2026-09-23",
        "name": "Movilidad y core",
        "notes": "20 minutos de movilidad.",
    }

    workout_session_id = payload["workout_session"]["id"]

    with get_connection() as connection:
        exercise_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM workout_exercises
            WHERE workout_session_id = ?
            """,
            (workout_session_id,),
        ).fetchone()["count"]

    assert exercise_count == 0
def test_complete_planned_workout_copies_template_exercises_and_sets():
    with TestClient(app) as client:
        headers = register_and_login(client)
        template = create_template(
            client,
            headers=headers,
            name="Torso A",
            notes="Plantilla de torso.",
        )
        press = create_template_exercise(
            client,
            headers=headers,
            template_id=template["id"],
            name="Press banca",
            muscle_group="Pectoral",
            position=1,
        )
        row = create_template_exercise(
            client,
            headers=headers,
            template_id=template["id"],
            name="Remo con barra",
            muscle_group="Espalda",
            position=2,
        )
        create_template_set(
            client,
            headers=headers,
            exercise_id=press["id"],
            position=1,
            repetitions=8,
            weight_kg=70.0,
        )
        create_template_set(
            client,
            headers=headers,
            exercise_id=press["id"],
            position=2,
            repetitions=10,
            weight_kg=60.0,
            rir=1.0,
        )
        create_template_set(
            client,
            headers=headers,
            exercise_id=row["id"],
            position=1,
            repetitions=12,
            weight_kg=50.0,
        )

        planned_workout = create_planned_workout(
            client,
            headers=headers,
            scheduled_date="2026-09-22",
            workout_template_id=template["id"],
            name=None,
            notes="Completar la rutina.",
        )

        complete_response = client.post(
            f"/planned-workouts/{planned_workout['id']}/complete",
            headers=headers,
            json={},
        )
        session_id = complete_response.json()["workout_session"]["id"]
    

    assert complete_response.status_code == 201
    completed = complete_response.json()
    assert completed["planned_workout"]["status"] == "completed"
    assert completed["workout_session"]["date"] == "2026-09-22"
    assert completed["workout_session"]["name"] == "Torso A"
    assert completed["workout_session"]["notes"] == "Completar la rutina."

    with get_connection() as connection:
        exercises = connection.execute(
            """
            SELECT
                id,
                name,
                muscle_group,
                position,
                technique_notes
            FROM workout_exercises
            WHERE workout_session_id = ?
            ORDER BY position ASC, id ASC
            """,
            (session_id,),
        ).fetchall()

        press_sets = connection.execute(
            """
            SELECT
                position,
                repetitions,
                weight_kg,
                rir
            FROM workout_sets
            WHERE workout_exercise_id = ?
            ORDER BY position ASC, id ASC
            """,
            (exercises[0]["id"],),
        ).fetchall()

        row_sets = connection.execute(
            """
            SELECT
                position,
                repetitions,
                weight_kg,
                rir
            FROM workout_sets
            WHERE workout_exercise_id = ?
            ORDER BY position ASC, id ASC
            """,
            (exercises[1]["id"],),
        ).fetchall()

    assert [
        (
            exercise["name"],
            exercise["muscle_group"],
            exercise["position"],
        )
        for exercise in exercises
    ] == [
        ("Press banca", "Pectoral", 1),
        ("Remo con barra", "Espalda", 2),
    ]

    assert [
        (
            workout_set["position"],
            workout_set["repetitions"],
            workout_set["weight_kg"],
            workout_set["rir"],
        )
        for workout_set in press_sets
    ] == [
        (1, 8, 70.0, 2.0),
        (2, 10, 60.0, 1.0),
    ]

    assert [
        (
            workout_set["position"],
            workout_set["repetitions"],
            workout_set["weight_kg"],
            workout_set["rir"],
        )
        for workout_set in row_sets
    ] == [
        (1, 12, 50.0, 2.0),
    ]
    

def test_complete_planned_workout_twice_returns_conflict():
    with TestClient(app) as client:
        headers = register_and_login(client)
        planned_workout = create_planned_workout(
            client,
            headers=headers,
        )

        first_response = client.post(
            f"/planned-workouts/{planned_workout['id']}/complete",
            headers=headers,
            json={},
        )
        second_response = client.post(
            f"/planned-workouts/{planned_workout['id']}/complete",
            headers=headers,
            json={},
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "La sesión planificada ya está completada."
    }


def test_complete_skipped_planned_workout_returns_conflict():
    with TestClient(app) as client:
        headers = register_and_login(client)
        planned_workout = create_planned_workout(
            client,
            headers=headers,
        )

        update_response = client.put(
            f"/planned-workouts/{planned_workout['id']}",
            headers=headers,
            json={
                "scheduled_date": planned_workout["scheduled_date"],
                "workout_template_id": None,
                "name": planned_workout["name"],
                "notes": planned_workout["notes"],
                "status": "skipped",
            },
        )
        complete_response = client.post(
            f"/planned-workouts/{planned_workout['id']}/complete",
            headers=headers,
            json={},
        )

    assert update_response.status_code == 200
    assert complete_response.status_code == 409
    assert complete_response.json() == {
        "detail": "No se puede completar una sesión planificada omitida."
    }


def test_completed_planned_workout_cannot_be_updated_or_deleted():
    with TestClient(app) as client:
        headers = register_and_login(client)
        planned_workout = create_planned_workout(
            client,
            headers=headers,
        )

        complete_response = client.post(
            f"/planned-workouts/{planned_workout['id']}/complete",
            headers=headers,
            json={},
        )
        update_response = client.put(
            f"/planned-workouts/{planned_workout['id']}",
            headers=headers,
            json={
                "scheduled_date": "2026-09-25",
                "workout_template_id": None,
                "name": "No debe cambiar",
                "notes": None,
                "status": "planned",
            },
        )
        delete_response = client.delete(
            f"/planned-workouts/{planned_workout['id']}",
            headers=headers,
        )

    assert complete_response.status_code == 201
    assert update_response.status_code == 409
    assert update_response.json() == {
        "detail": "No se puede modificar una sesión planificada completada."
    }
    assert delete_response.status_code == 409
    assert delete_response.json() == {
        "detail": "No se puede eliminar una sesión planificada completada."
    }


def test_users_have_isolated_planned_workouts():
    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana-planned-workouts@example.com",
            display_name="Ana Planned Workouts",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno-planned-workouts@example.com",
            display_name="Bruno Planned Workouts",
        )
        ana_planned_workout = create_planned_workout(
            client,
            headers=ana_headers,
            name="Plan de Ana",
        )

        get_response = client.get(
            f"/planned-workouts/{ana_planned_workout['id']}",
            headers=bruno_headers,
        )
        update_response = client.put(
            f"/planned-workouts/{ana_planned_workout['id']}",
            headers=bruno_headers,
            json={
                "scheduled_date": "2026-09-25",
                "workout_template_id": None,
                "name": "Plan manipulado",
                "notes": None,
                "status": "planned",
            },
        )
        delete_response = client.delete(
            f"/planned-workouts/{ana_planned_workout['id']}",
            headers=bruno_headers,
        )
        complete_response = client.post(
            f"/planned-workouts/{ana_planned_workout['id']}/complete",
            headers=bruno_headers,
            json={},
        )

    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404
    assert complete_response.status_code == 404