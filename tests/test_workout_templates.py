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