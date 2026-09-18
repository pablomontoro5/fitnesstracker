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
    weight_kg: float = 60,
    rir: float | None = 2,
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

def test_create_workout_template():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/workout-templates/",
            headers=headers,
            json={
                "name": "Torso A",
                "notes": "Rutina principal de torso.",
            },
        )

    assert response.status_code == 201

def test_list_workout_templates():
    with TestClient(app) as client:
        headers = register_and_login(client)
        workout_template = create_template(client, headers=headers)
        response = client.get("/workout-templates/", headers=headers)

    assert response.status_code == 200
    assert any(
        item["id"] == workout_template["id"]
        for item in response.json()
    )


def test_get_workout_template():
    with TestClient(app) as client:
        headers = register_and_login(client)
        workout_template = create_template(
            client,
            headers=headers,
            name="Pierna A",
            notes=None,
        )
        response = client.get(
            f"/workout-templates/{workout_template['id']}",
            headers=headers
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Pierna A"
    assert response.json()["notes"] is None


def test_delete_workout_template():
    with TestClient(app) as client:
        headers = register_and_login(client)
        workout_template = create_template(client, headers=headers)

        delete_response = client.delete(
            f"/workout-templates/{workout_template['id']}",
            headers=headers
        )
        get_response = client.get(
            f"/workout-templates/{workout_template['id']}",
            headers=headers
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_empty_workout_template_name_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.post(
            "/workout-templates/",
            headers=headers,
            json={
                "name": "",
                "notes": None,
            },
        )

    assert response.status_code == 422

def test_create_and_list_workout_template_exercises():
    with TestClient(app) as client:
        headers = register_and_login(client)

        workout_template = create_template(
            client,
            headers=headers,
        )

        second_exercise = create_template_exercise(
            client,
            headers=headers,
            template_id=workout_template["id"],
            name="Remo con barra",
            muscle_group="Espalda",
            position=2,
            technique_notes=None,
        )

        first_exercise = create_template_exercise(
            client,
            headers=headers,
            template_id=workout_template["id"],
            name="Press banca",
            muscle_group="Pectoral",
            position=1,
        )

        response = client.get(
            f"/workout-templates/{workout_template['id']}/exercises/",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == [
        first_exercise,
        second_exercise,
    ]


def test_workout_template_exercise_requires_existing_template():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.post(
            "/workout-templates/999999/exercises/",
            headers=headers,
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
        headers = register_and_login(client)
        workout_template = create_template(client, headers=headers)

        create_template_exercise(
            client,
            template_id=workout_template["id"],
            position=1,
            headers=headers
        )

        response = client.post(
            f"/workout-templates/{workout_template['id']}/exercises/",
            headers=headers,
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
        headers = register_and_login(client)
        workout_template = create_template(client, headers=headers)
        workout_template_exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
            headers=headers
        )

        update_response = client.put(
            f"/workout-templates/exercises/{workout_template_exercise['id']}",
            headers=headers,
            json={
                "name": "Press inclinado",
                "muscle_group": "Pectoral",
                "position": 2,
                "technique_notes": "Controlar la bajada.",
            },
        )
        delete_response = client.delete(
            f"/workout-templates/exercises/{workout_template_exercise['id']}",
            headers=headers
        )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Press inclinado"
    assert update_response.json()["position"] == 2

    assert delete_response.status_code == 204
def test_create_and_list_workout_template_sets():
    with TestClient(app) as client:
        headers = register_and_login(client)

        workout_template = create_template(
            client,
            headers=headers,
        )
        workout_template_exercise = create_template_exercise(
            client,
            headers=headers,
            template_id=workout_template["id"],
        )

        second_set = create_template_set(
            client,
            headers=headers,
            exercise_id=workout_template_exercise["id"],
            position=2,
            repetitions=8,
            weight_kg=70.0,
        )
        first_set = create_template_set(
            client,
            headers=headers,
            exercise_id=workout_template_exercise["id"],
            position=1,
            repetitions=10,
            weight_kg=60.0,
        )

        response = client.get(
            (
                "/workout-templates/exercises/"
                f"{workout_template_exercise['id']}/sets/"
            ),
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == [
        first_set,
        second_set,
    ]

def test_workout_template_set_requires_existing_exercise():
    with TestClient(app) as client:
        headers = register_and_login(client)
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
            headers=headers
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existe un ejercicio de plantilla con ese id."
    )


def test_workout_template_set_position_must_be_unique():
    with TestClient(app) as client:
        headers = register_and_login(client)

        workout_template = create_template(
            client,
            headers=headers,
        )
        workout_template_exercise = create_template_exercise(
            client,
            headers=headers,
            template_id=workout_template["id"],
        )

        create_template_set(
            client,
            headers=headers,
            exercise_id=workout_template_exercise["id"],
            position=1,
        )

        response = client.post(
            (
                "/workout-templates/exercises/"
                f"{workout_template_exercise['id']}/sets/"
            ),
            headers=headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 8,
                "weight_kg": 70.0,
                "rir": 1.0,
                "notes": None,
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Ya existe una serie en esa posición "
            "para este ejercicio de plantilla."
        )
    }

def test_update_and_delete_workout_template_set():
    with TestClient(app) as client:
        headers = register_and_login(client)
        workout_template = create_template(client, headers=headers)
        exercise = create_template_exercise(
            client,
            template_id=workout_template["id"],
            headers=headers
        )
        workout_template_set = create_template_set(
            client,
            exercise_id=exercise["id"],
            headers=headers
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
            headers=headers
        )
        delete_response = client.delete(
            f"/workout-templates/sets/{workout_template_set['id']}",
            headers=headers
        )

    assert update_response.status_code == 200
    assert update_response.json()["set_type"] == "drop_set"
    assert update_response.json()["position"] == 2
    assert update_response.json()["volume_kg"] == 480

    assert delete_response.status_code == 204

def test_create_session_from_workout_template_copies_exercises_and_sets():
    with TestClient(app) as client:
        headers = register_and_login(client)

        workout_template = create_template(
            client,
            headers=headers,
            name="Pierna A",
            notes="Sentadilla y peso muerto rumano.",
        )
        squat = create_template_exercise(
            client,
            headers=headers,
            template_id=workout_template["id"],
            name="Sentadilla trasera",
            muscle_group="Cuádriceps",
            position=1,
        )
        create_template_set(
            client,
            headers=headers,
            exercise_id=squat["id"],
            position=1,
            repetitions=5,
            weight_kg=100.0,
        )

        response = client.post(
            (
                "/workout-templates/"
                f"{workout_template['id']}/create-session"
            ),
            headers=headers,
        )

    assert response.status_code == 201
def test_create_session_from_missing_workout_template_returns_404():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/workout-templates/999999/create-session",
            headers=headers,
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existe una plantilla con ese id."
    )

def test_users_have_isolated_workout_templates():
    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana-templates@example.com",
            display_name="Ana Templates",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno-templates@example.com",
            display_name="Bruno Templates",
        )

        ana_template = create_template(
            client,
            headers=ana_headers,
            name="Torso de Ana",
        )
        bruno_template = create_template(
            client,
            headers=bruno_headers,
            name="Pierna de Bruno",
        )

        ana_list_response = client.get(
            "/workout-templates/",
            headers=ana_headers,
        )
        bruno_list_response = client.get(
            "/workout-templates/",
            headers=bruno_headers,
        )
        other_get_response = client.get(
            f"/workout-templates/{ana_template['id']}",
            headers=bruno_headers,
        )
        other_delete_response = client.delete(
            f"/workout-templates/{ana_template['id']}",
            headers=bruno_headers,
        )

    assert ana_list_response.status_code == 200
    assert bruno_list_response.status_code == 200
    assert ana_list_response.json() == [ana_template]
    assert bruno_list_response.json() == [bruno_template]
    assert other_get_response.status_code == 404
    assert other_delete_response.status_code == 404

def test_user_cannot_modify_another_users_template_set():
    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana-template-set@example.com",
            display_name="Ana Template Set",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno-template-set@example.com",
            display_name="Bruno Template Set",
        )

        ana_template = create_template(
            client,
            headers=ana_headers,
            name="Plantilla de Ana",
        )
        ana_exercise = create_template_exercise(
            client,
            headers=ana_headers,
            template_id=ana_template["id"],
        )
        ana_set = create_template_set(
            client,
            headers=ana_headers,
            exercise_id=ana_exercise["id"],
        )

        update_response = client.put(
            f"/workout-templates/sets/{ana_set['id']}",
            headers=bruno_headers,
            json={
                "set_type": "working",
                "position": 1,
                "target_rep_range": "8-12",
                "repetitions": 15,
                "weight_kg": 100.0,
                "rir": 0.0,
                "notes": None,
            },
        )
        delete_response = client.delete(
            f"/workout-templates/sets/{ana_set['id']}",
            headers=bruno_headers,
        )
        create_session_response = client.post(
            (
                "/workout-templates/"
                f"{ana_template['id']}/create-session"
            ),
            headers=bruno_headers,
        )

    assert update_response.status_code == 404
    assert delete_response.status_code == 404
    assert create_session_response.status_code == 404