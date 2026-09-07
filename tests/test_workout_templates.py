from fastapi.testclient import TestClient

from app.main import app


def create_template(
    client: TestClient,
    *,
    name: str = "Torso A",
    notes: str | None = "Rutina principal de torso.",
) -> dict:
    response = client.post(
        "/workout-templates/",
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
    template_id: int,
    name: str = "Press banca",
    muscle_group: str = "Pectoral",
    position: int = 1,
    technique_notes: str | None = "Escápulas retraídas.",
) -> dict:
    response = client.post(
        f"/workout-templates/{template_id}/exercises/",
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
    exercise_id: int,
    set_type: str = "working",
    position: int = 1,
    target_rep_range: str | None = "8-12",
    repetitions: int = 10,
    weight_kg: float = 60,
    rir: float | None = 2,
    notes: str | None = "Mantener la técnica.",
) -> dict:
    response = client.post(
        f"/workout-templates/exercises/{exercise_id}/sets/",
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

def test_create_workout_template():
    with TestClient(app) as client:
        workout_template = create_template(client)

    assert workout_template["name"] == "Torso A"
    assert workout_template["notes"] == "Rutina principal de torso."
    assert isinstance(workout_template["id"], int)


def test_list_workout_templates():
    with TestClient(app) as client:
        workout_template = create_template(client)
        response = client.get("/workout-templates/")

    assert response.status_code == 200
    assert any(
        item["id"] == workout_template["id"]
        for item in response.json()
    )


def test_get_workout_template():
    with TestClient(app) as client:
        workout_template = create_template(
            client,
            name="Pierna A",
            notes=None,
        )
        response = client.get(
            f"/workout-templates/{workout_template['id']}"
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Pierna A"
    assert response.json()["notes"] is None


def test_delete_workout_template():
    with TestClient(app) as client:
        workout_template = create_template(client)

        delete_response = client.delete(
            f"/workout-templates/{workout_template['id']}"
        )
        get_response = client.get(
            f"/workout-templates/{workout_template['id']}"
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_empty_workout_template_name_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/workout-templates/",
            json={
                "name": "",
                "notes": None,
            },
        )

    assert response.status_code == 422

def test_create_and_list_workout_template_exercises():
    with TestClient(app) as client:
        workout_template = create_template(client)

        second_exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
            name="Remo con barra",
            muscle_group="Espalda",
            position=2,
            technique_notes=None,
        )
        first_exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
            name="Press banca",
            muscle_group="Pectoral",
            position=1,
        )

        response = client.get(
            f"/workout-templates/{workout_template['id']}/exercises/"
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": first_exercise["id"],
            "workout_template_id": workout_template["id"],
            "name": "Press banca",
            "muscle_group": "Pectoral",
            "position": 1,
            "technique_notes": "Escápulas retraídas.",
        },
        {
            "id": second_exercise["id"],
            "workout_template_id": workout_template["id"],
            "name": "Remo con barra",
            "muscle_group": "Espalda",
            "position": 2,
            "technique_notes": None,
        },
    ]


def test_workout_template_exercise_requires_existing_template():
    with TestClient(app) as client:
        response = client.post(
            "/workout-templates/999999/exercises/",
            json={
                "name": "Sentadilla",
                "muscle_group": "Cuádriceps",
                "position": 1,
                "technique_notes": None,
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existe una plantilla con ese id."
    )


def test_workout_template_exercise_position_must_be_unique():
    with TestClient(app) as client:
        workout_template = create_template(client)

        create_template_exercise(
            client,
            template_id=workout_template["id"],
            position=1,
        )

        response = client.post(
            f"/workout-templates/{workout_template['id']}/exercises/",
            json={
                "name": "Remo con barra",
                "muscle_group": "Espalda",
                "position": 1,
                "technique_notes": None,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe un ejercicio en esa posición para esta plantilla."
    )


def test_update_and_delete_workout_template_exercise():
    with TestClient(app) as client:
        workout_template = create_template(client)
        workout_template_exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
        )

        update_response = client.put(
            f"/workout-templates/exercises/{workout_template_exercise['id']}",
            json={
                "name": "Press inclinado",
                "muscle_group": "Pectoral",
                "position": 2,
                "technique_notes": "Controlar la bajada.",
            },
        )
        delete_response = client.delete(
            f"/workout-templates/exercises/{workout_template_exercise['id']}"
        )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Press inclinado"
    assert update_response.json()["position"] == 2

    assert delete_response.status_code == 204
def test_create_and_list_workout_template_sets():
    with TestClient(app) as client:
        workout_template = create_template(client)
        exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
        )

        second_set = create_template_set(
            client,
            exercise_id=exercise["id"],
            position=2,
            repetitions=8,
            weight_kg=70,
            notes=None,
        )
        first_set = create_template_set(
            client,
            exercise_id=exercise["id"],
            position=1,
            repetitions=10,
            weight_kg=60,
        )

        response = client.get(
            f"/workout-templates/exercises/{exercise['id']}/sets/"
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": first_set["id"],
            "workout_template_exercise_id": exercise["id"],
            "set_type": "working",
            "position": 1,
            "target_rep_range": "8-12",
            "repetitions": 10,
            "weight_kg": 60,
            "rir": 2,
            "notes": "Mantener la técnica.",
            "volume_kg": 600,
        },
        {
            "id": second_set["id"],
            "workout_template_exercise_id": exercise["id"],
            "set_type": "working",
            "position": 2,
            "target_rep_range": "8-12",
            "repetitions": 8,
            "weight_kg": 70,
            "rir": 2,
            "notes": None,
            "volume_kg": 560,
        },
    ]


def test_workout_template_set_requires_existing_exercise():
    with TestClient(app) as client:
        response = client.post(
            "/workout-templates/exercises/999999/sets/",
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

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existe un ejercicio de plantilla con ese id."
    )


def test_workout_template_set_position_must_be_unique():
    with TestClient(app) as client:
        workout_template = create_template(client)
        exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
        )

        create_template_set(
            client,
            exercise_id=exercise["id"],
            position=1,
        )

        response = client.post(
            f"/workout-templates/exercises/{exercise['id']}/sets/",
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 8,
                "weight_kg": 70,
                "rir": 1,
                "notes": None,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe una serie en esa posición "
        "para este ejercicio de plantilla."
    )


def test_update_and_delete_workout_template_set():
    with TestClient(app) as client:
        workout_template = create_template(client)
        exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
        )
        workout_template_set = create_template_set(
            client,
            exercise_id=exercise["id"],
        )

        update_response = client.put(
            f"/workout-templates/sets/{workout_template_set['id']}",
            json={
                "set_type": "drop_set",
                "position": 2,
                "target_rep_range": "12-15",
                "repetitions": 12,
                "weight_kg": 40,
                "rir": 1,
                "notes": "Bajar carga sin descanso.",
            },
        )
        delete_response = client.delete(
            f"/workout-templates/sets/{workout_template_set['id']}"
        )

    assert update_response.status_code == 200
    assert update_response.json()["set_type"] == "drop_set"
    assert update_response.json()["position"] == 2
    assert update_response.json()["volume_kg"] == 480

    assert delete_response.status_code == 204