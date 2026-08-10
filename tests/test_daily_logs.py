from fastapi.testclient import TestClient

from app.main import app


def test_create_daily_log():
    log_date = "2026-08-10"

    with TestClient(app) as client:
        client.delete(f"/daily-logs/{log_date}")

        response = client.post(
            "/daily-logs/",
            json={
                "date": log_date,
                "steps": 8000,
                "notes": "Paseo por la tarde.",
            },
        )

    assert response.status_code == 201
    assert response.json()["date"] == log_date
    assert response.json()["steps"] == 8000
    assert response.json()["notes"] == "Paseo por la tarde."


def test_get_daily_log():
    log_date = "2026-08-11"

    with TestClient(app) as client:
        client.delete(f"/daily-logs/{log_date}")

        client.post(
            "/daily-logs/",
            json={
                "date": log_date,
                "steps": 6500,
                "notes": None,
            },
        )

        response = client.get(f"/daily-logs/{log_date}")

    assert response.status_code == 200
    assert response.json()["steps"] == 6500


def test_update_daily_log():
    log_date = "2026-08-12"

    with TestClient(app) as client:
        client.delete(f"/daily-logs/{log_date}")

        client.post(
            "/daily-logs/",
            json={
                "date": log_date,
                "steps": 4000,
                "notes": "Registro inicial.",
            },
        )

        response = client.put(
            f"/daily-logs/{log_date}",
            json={
                "steps": 10000,
                "notes": "Objetivo diario completado.",
            },
        )

    assert response.status_code == 200
    assert response.json()["steps"] == 10000
    assert response.json()["notes"] == "Objetivo diario completado."


def test_delete_daily_log():
    log_date = "2026-08-13"

    with TestClient(app) as client:
        client.delete(f"/daily-logs/{log_date}")

        client.post(
            "/daily-logs/",
            json={
                "date": log_date,
                "steps": 7000,
                "notes": None,
            },
        )

        delete_response = client.delete(f"/daily-logs/{log_date}")
        get_response = client.get(f"/daily-logs/{log_date}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_duplicate_date_returns_conflict():
    log_date = "2026-08-14"

    with TestClient(app) as client:
        client.delete(f"/daily-logs/{log_date}")

        payload = {
            "date": log_date,
            "steps": 9000,
            "notes": None,
        }

        first_response = client.post("/daily-logs/", json=payload)
        second_response = client.post("/daily-logs/", json=payload)

        client.delete(f"/daily-logs/{log_date}")

    assert first_response.status_code == 201
    assert second_response.status_code == 409