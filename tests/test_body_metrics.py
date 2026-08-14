from fastapi.testclient import TestClient

from app.main import app


def test_create_body_metric_calculates_bmi():
    log_date = "2026-08-14"

    with TestClient(app) as client:
        client.delete("/body-metrics/1")

        response = client.post(
            "/body-metrics/",
            json={
                "date": log_date,
                "weight_kg": 80,
                "height_cm": 180,
                "notes": "Medición inicial.",
            },
        )

    assert response.status_code == 201
    assert response.json()["weight_kg"] == 80
    assert response.json()["height_cm"] == 180
    assert response.json()["bmi"] == 24.69
    assert response.json()["notes"] == "Medición inicial."


def test_list_body_metrics():
    log_date = "2026-08-15"

    with TestClient(app) as client:
        client.post(
            "/body-metrics/",
            json={
                "date": log_date,
                "weight_kg": 75,
                "height_cm": 175,
                "notes": None,
            },
        )

        response = client.get("/body-metrics/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_invalid_body_metric_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/body-metrics/",
            json={
                "date": "2026-08-16",
                "weight_kg": -10,
                "height_cm": 180,
                "notes": None,
            },
        )

    assert response.status_code == 422