from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_body_metric(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str,
    weight_kg: float = 80,
    height_cm: float = 180,
    body_fat_percentage: float | None = None,
    waist_cm: float | None = None,
    hip_cm: float | None = None,
    chest_cm: float | None = None,
    arm_cm: float | None = None,
    thigh_cm: float | None = None,
    notes: str | None = None,
) -> dict:
    response = client.post(
        "/body-metrics/",
        headers=headers,
        json={
            "date": date,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "body_fat_percentage": body_fat_percentage,
            "waist_cm": waist_cm,
            "hip_cm": hip_cm,
            "chest_cm": chest_cm,
            "arm_cm": arm_cm,
            "thigh_cm": thigh_cm,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_body_metric_calculates_bmi():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/body-metrics/",
            headers=headers,
            json={
                "date": "2026-08-14",
                "weight_kg": 80,
                "height_cm": 180,
                "notes": "Medición inicial.",
            },
        )

    assert response.status_code == 201
    assert response.json()["weight_kg"] == 80
    assert response.json()["height_cm"] == 180
    assert response.json()["bmi"] == 24.69
    assert response.json()["body_fat_percentage"] is None
    assert response.json()["fat_mass_kg"] is None
    assert response.json()["lean_mass_kg"] is None
    assert response.json()["notes"] == "Medición inicial."


def test_create_body_metric_calculates_body_composition():
    with TestClient(app) as client:
        headers = register_and_login(client)

        body_metric = create_body_metric(
            client,
            headers=headers,
            date="2026-08-15",
            weight_kg=80,
            height_cm=180,
            body_fat_percentage=18,
            waist_cm=84,
            chest_cm=103,
            arm_cm=38,
            thigh_cm=59,
            notes="Medición matinal.",
        )

    assert body_metric["bmi"] == 24.69
    assert body_metric["body_fat_percentage"] == 18
    assert body_metric["fat_mass_kg"] == 14.4
    assert body_metric["lean_mass_kg"] == 65.6
    assert body_metric["waist_cm"] == 84
    assert body_metric["hip_cm"] is None
    assert body_metric["chest_cm"] == 103
    assert body_metric["arm_cm"] == 38
    assert body_metric["thigh_cm"] == 59


def test_list_body_metrics():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_body_metric(
            client,
            headers=headers,
            date="2026-08-16",
            weight_kg=75,
            height_cm=175,
        )

        response = client.get(
            "/body-metrics/",
            headers=headers,
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["date"] == "2026-08-16"


def test_update_body_metric_updates_composition():
    with TestClient(app) as client:
        headers = register_and_login(client)

        body_metric = create_body_metric(
            client,
            headers=headers,
            date="2026-08-17",
            weight_kg=80,
            height_cm=180,
        )

        response = client.put(
            f"/body-metrics/{body_metric['id']}",
            headers=headers,
            json={
                "date": "2026-08-17",
                "weight_kg": 79.5,
                "height_cm": 180,
                "body_fat_percentage": 17.5,
                "waist_cm": 83,
                "hip_cm": 97,
                "chest_cm": 102,
                "arm_cm": 37.5,
                "thigh_cm": 58.5,
                "notes": "Medición actualizada.",
            },
        )

    assert response.status_code == 200
    assert response.json()["weight_kg"] == 79.5
    assert response.json()["bmi"] == 24.54
    assert response.json()["body_fat_percentage"] == 17.5
    assert response.json()["fat_mass_kg"] == 13.91
    assert response.json()["lean_mass_kg"] == 65.59
    assert response.json()["waist_cm"] == 83
    assert response.json()["hip_cm"] == 97


def test_invalid_body_metric_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/body-metrics/",
            headers=headers,
            json={
                "date": "2026-08-18",
                "weight_kg": -10,
                "height_cm": 180,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_invalid_body_fat_percentage_is_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.post(
            "/body-metrics/",
            headers=headers,
            json={
                "date": "2026-08-19",
                "weight_kg": 80,
                "height_cm": 180,
                "body_fat_percentage": 100,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_body_composition_progress_returns_records_and_changes():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_body_metric(
            client,
            headers=headers,
            date="2026-09-01",
            weight_kg=80,
            height_cm=180,
            body_fat_percentage=20,
            waist_cm=85,
            chest_cm=102,
        )
        create_body_metric(
            client,
            headers=headers,
            date="2026-09-10",
            weight_kg=78,
            height_cm=180,
            body_fat_percentage=18,
            waist_cm=83,
            chest_cm=103,
        )

        response = client.get(
            "/body-metrics/progress",
            headers=headers,
            params={
                "start_date": "2026-09-01",
                "end_date": "2026-09-10",
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["start_date"] == "2026-09-01"
    assert body["end_date"] == "2026-09-10"
    assert [record["date"] for record in body["records"]] == [
        "2026-09-01",
        "2026-09-10",
    ]

    assert body["records"][0]["fat_mass_kg"] == 16
    assert body["records"][0]["lean_mass_kg"] == 64
    assert body["records"][1]["fat_mass_kg"] == 14.04
    assert body["records"][1]["lean_mass_kg"] == 63.96

    assert body["changes"] == {
        "weight_kg": -2,
        "bmi": -0.62,
        "body_fat_percentage": -2,
        "fat_mass_kg": -1.96,
        "lean_mass_kg": -0.04,
        "waist_cm": -2,
        "hip_cm": None,
        "chest_cm": 1,
        "arm_cm": None,
        "thigh_cm": None,
    }


def test_body_composition_progress_uses_first_and_last_available_value():
    with TestClient(app) as client:
        headers = register_and_login(client)

        create_body_metric(
            client,
            headers=headers,
            date="2026-09-11",
            weight_kg=80,
            body_fat_percentage=None,
            waist_cm=85,
        )
        create_body_metric(
            client,
            headers=headers,
            date="2026-09-12",
            weight_kg=79,
            body_fat_percentage=20,
            waist_cm=None,
        )
        create_body_metric(
            client,
            headers=headers,
            date="2026-09-13",
            weight_kg=78,
            body_fat_percentage=18,
            waist_cm=83,
        )

        response = client.get(
            "/body-metrics/progress",
            headers=headers,
            params={
                "start_date": "2026-09-11",
                "end_date": "2026-09-13",
            },
        )

    assert response.status_code == 200
    assert response.json()["changes"]["weight_kg"] == -2
    assert response.json()["changes"]["body_fat_percentage"] == -2
    assert response.json()["changes"]["waist_cm"] == -2


def test_body_composition_progress_returns_empty_data_for_empty_period():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.get(
            "/body-metrics/progress",
            headers=headers,
            params={
                "start_date": "2030-01-01",
                "end_date": "2030-01-31",
            },
        )

    assert response.status_code == 200
    assert response.json()["records"] == []
    assert response.json()["changes"] == {
        "weight_kg": None,
        "bmi": None,
        "body_fat_percentage": None,
        "fat_mass_kg": None,
        "lean_mass_kg": None,
        "waist_cm": None,
        "hip_cm": None,
        "chest_cm": None,
        "arm_cm": None,
        "thigh_cm": None,
    }


def test_body_composition_progress_rejects_inverted_date_range():
    with TestClient(app) as client:
        headers = register_and_login(client)

        response = client.get(
            "/body-metrics/progress",
            headers=headers,
            params={
                "start_date": "2026-09-10",
                "end_date": "2026-09-01",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "start_date no puede ser posterior a end_date."
    )


def test_users_have_isolated_body_metrics_and_can_share_dates():
    with TestClient(app) as client:
        first_headers = register_and_login(
            client,
            email="body-first@example.com",
            display_name="Body First",
        )
        second_headers = register_and_login(
            client,
            email="body-second@example.com",
            display_name="Body Second",
        )

        first_metric = create_body_metric(
            client,
            headers=first_headers,
            date="2026-09-20",
            weight_kg=80,
        )
        second_metric = create_body_metric(
            client,
            headers=second_headers,
            date="2026-09-20",
            weight_kg=70,
        )

        first_list_response = client.get(
            "/body-metrics/",
            headers=first_headers,
        )
        second_list_response = client.get(
            "/body-metrics/",
            headers=second_headers,
        )
        other_get_response = client.get(
            f"/body-metrics/{first_metric['id']}",
            headers=second_headers,
        )
        other_update_response = client.put(
            f"/body-metrics/{first_metric['id']}",
            headers=second_headers,
            json={
                "date": "2026-09-20",
                "weight_kg": 99,
                "height_cm": 180,
                "body_fat_percentage": None,
                "waist_cm": None,
                "hip_cm": None,
                "chest_cm": None,
                "arm_cm": None,
                "thigh_cm": None,
                "notes": "Intento no autorizado.",
            },
        )
        other_delete_response = client.delete(
            f"/body-metrics/{first_metric['id']}",
            headers=second_headers,
        )
        other_progress_response = client.get(
            "/body-metrics/progress",
            headers=second_headers,
            params={
                "start_date": "2026-09-20",
                "end_date": "2026-09-20",
            },
        )

    assert first_list_response.status_code == 200
    assert second_list_response.status_code == 200
    assert [metric["id"] for metric in first_list_response.json()] == [
        first_metric["id"]
    ]
    assert [metric["id"] for metric in second_list_response.json()] == [
        second_metric["id"]
    ]
    assert other_get_response.status_code == 404
    assert other_update_response.status_code == 404
    assert other_delete_response.status_code == 404
    assert other_progress_response.status_code == 200
    assert [
        record["weight_kg"]
        for record in other_progress_response.json()["records"]
    ] == [70]