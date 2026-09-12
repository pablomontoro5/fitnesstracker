from fastapi.testclient import TestClient

from app.main import app


def create_recovery_log(
    client: TestClient,
    *,
    log_date: str = "2026-09-09",
    sleep_minutes: int | None = 450,
    sleep_quality: int | None = 4,
    is_rest_day: bool = False,
    notes: str | None = "Movilidad suave.",
) -> dict:
    response = client.post(
        "/recovery-logs/",
        json={
            "date": log_date,
            "sleep_minutes": sleep_minutes,
            "sleep_quality": sleep_quality,
            "is_rest_day": is_rest_day,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_recovery_log():
    with TestClient(app) as client:
        recovery_log = create_recovery_log(client)

    assert recovery_log == {
        "id": recovery_log["id"],
        "date": "2026-09-09",
        "sleep_minutes": 450,
        "sleep_quality": 4,
        "is_rest_day": False,
        "notes": "Movilidad suave.",
    }


def test_create_recovery_log_allows_rest_day_without_sleep_data():
    with TestClient(app) as client:
        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-09",
                "sleep_minutes": None,
                "sleep_quality": None,
                "is_rest_day": True,
                "notes": None,
            },
        )

    assert response.status_code == 201
    assert response.json()["sleep_minutes"] is None
    assert response.json()["sleep_quality"] is None
    assert response.json()["is_rest_day"] is True


def test_create_duplicate_recovery_log_returns_conflict():
    with TestClient(app) as client:
        create_recovery_log(client)

        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-09",
                "sleep_minutes": 480,
                "sleep_quality": 5,
                "is_rest_day": True,
                "notes": None,
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Ya existe un registro de recuperación para esta fecha."
    }


def test_list_recovery_logs_returns_descending_date_order():
    with TestClient(app) as client:
        create_recovery_log(
            client,
            log_date="2026-09-07",
            sleep_minutes=420,
        )
        create_recovery_log(
            client,
            log_date="2026-09-09",
            sleep_minutes=480,
        )
        create_recovery_log(
            client,
            log_date="2026-09-08",
            sleep_minutes=450,
        )

        response = client.get("/recovery-logs/")

    assert response.status_code == 200
    assert [recovery_log["date"] for recovery_log in response.json()] == [
        "2026-09-09",
        "2026-09-08",
        "2026-09-07",
    ]


def test_get_recovery_log_by_date():
    with TestClient(app) as client:
        created_log = create_recovery_log(client)

        response = client.get("/recovery-logs/2026-09-09")

    assert response.status_code == 200
    assert response.json() == created_log


def test_get_missing_recovery_log_returns_not_found():
    with TestClient(app) as client:
        response = client.get("/recovery-logs/2026-09-09")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe un registro de recuperación para esta fecha."
    }


def test_update_recovery_log():
    with TestClient(app) as client:
        created_log = create_recovery_log(client)

        response = client.put(
            "/recovery-logs/2026-09-09",
            json={
                "sleep_minutes": 480,
                "sleep_quality": 5,
                "is_rest_day": True,
                "notes": "Descanso completo.",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": created_log["id"],
        "date": "2026-09-09",
        "sleep_minutes": 480,
        "sleep_quality": 5,
        "is_rest_day": True,
        "notes": "Descanso completo.",
    }


def test_update_missing_recovery_log_returns_not_found():
    with TestClient(app) as client:
        response = client.put(
            "/recovery-logs/2026-09-09",
            json={
                "sleep_minutes": 480,
                "sleep_quality": 5,
                "is_rest_day": True,
                "notes": None,
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe un registro de recuperación para esta fecha."
    }


def test_delete_recovery_log():
    with TestClient(app) as client:
        create_recovery_log(client)

        response = client.delete("/recovery-logs/2026-09-09")
        list_response = client.get("/recovery-logs/")

    assert response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_missing_recovery_log_returns_not_found():
    with TestClient(app) as client:
        response = client.delete("/recovery-logs/2026-09-09")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe un registro de recuperación para esta fecha."
    }


def test_recovery_log_rejects_invalid_sleep_minutes():
    with TestClient(app) as client:
        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-09",
                "sleep_minutes": 1441,
                "sleep_quality": 4,
                "is_rest_day": False,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_recovery_log_rejects_invalid_sleep_quality():
    with TestClient(app) as client:
        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-09",
                "sleep_minutes": 480,
                "sleep_quality": 6,
                "is_rest_day": False,
                "notes": None,
            },
        )

    assert response.status_code == 422