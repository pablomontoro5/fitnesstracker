from fastapi.testclient import TestClient

from app.main import app


def create_recovery_log(
    client: TestClient,
    *,
    log_date: str,
    sleep_minutes: int | None = None,
    sleep_quality: int | None = None,
    is_rest_day: bool = False,
    notes: str | None = None,
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
        recovery_log = create_recovery_log(
            client,
            log_date="2026-09-10",
            sleep_minutes=455,
            sleep_quality=4,
            is_rest_day=False,
            notes="Dormí bien y tuve energía.",
        )

    assert recovery_log["date"] == "2026-09-10"
    assert recovery_log["sleep_minutes"] == 455
    assert recovery_log["sleep_quality"] == 4
    assert recovery_log["is_rest_day"] is False
    assert recovery_log["notes"] == "Dormí bien y tuve energía."


def test_create_recovery_log_allows_rest_day_without_sleep():
    with TestClient(app) as client:
        recovery_log = create_recovery_log(
            client,
            log_date="2026-09-11",
            sleep_minutes=None,
            sleep_quality=None,
            is_rest_day=True,
            notes="Día de descanso.",
        )

    assert recovery_log["sleep_minutes"] is None
    assert recovery_log["sleep_quality"] is None
    assert recovery_log["is_rest_day"] is True


def test_list_recovery_logs_returns_descending_dates():
    with TestClient(app) as client:
        create_recovery_log(
            client,
            log_date="2026-09-10",
            sleep_minutes=450,
        )
        create_recovery_log(
            client,
            log_date="2026-09-12",
            sleep_minutes=480,
        )

        response = client.get("/recovery-logs/")

    assert response.status_code == 200
    assert [recovery_log["date"] for recovery_log in response.json()] == [
        "2026-09-12",
        "2026-09-10",
    ]


def test_get_recovery_log_by_date():
    with TestClient(app) as client:
        create_recovery_log(
            client,
            log_date="2026-09-13",
            sleep_minutes=420,
            sleep_quality=3,
        )

        response = client.get("/recovery-logs/2026-09-13")

    assert response.status_code == 200
    assert response.json()["sleep_minutes"] == 420
    assert response.json()["sleep_quality"] == 3


def test_update_recovery_log():
    with TestClient(app) as client:
        create_recovery_log(
            client,
            log_date="2026-09-14",
            sleep_minutes=400,
            sleep_quality=2,
            is_rest_day=False,
        )

        response = client.put(
            "/recovery-logs/2026-09-14",
            json={
                "sleep_minutes": 480,
                "sleep_quality": 5,
                "is_rest_day": True,
                "notes": "Actualizado.",
            },
        )

    assert response.status_code == 200
    assert response.json()["sleep_minutes"] == 480
    assert response.json()["sleep_quality"] == 5
    assert response.json()["is_rest_day"] is True
    assert response.json()["notes"] == "Actualizado."


def test_delete_recovery_log():
    with TestClient(app) as client:
        create_recovery_log(
            client,
            log_date="2026-09-15",
            sleep_minutes=480,
        )

        delete_response = client.delete("/recovery-logs/2026-09-15")
        get_response = client.get("/recovery-logs/2026-09-15")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_duplicate_recovery_log_date_returns_conflict():
    with TestClient(app) as client:
        create_recovery_log(
            client,
            log_date="2026-09-16",
            sleep_minutes=450,
        )

        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-16",
                "sleep_minutes": 460,
                "sleep_quality": 4,
                "is_rest_day": False,
                "notes": None,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe un registro de recuperación para esta fecha."
    )


def test_invalid_sleep_minutes_are_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-17",
                "sleep_minutes": 1441,
                "sleep_quality": 4,
                "is_rest_day": False,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_invalid_sleep_quality_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/recovery-logs/",
            json={
                "date": "2026-09-18",
                "sleep_minutes": 480,
                "sleep_quality": 6,
                "is_rest_day": False,
                "notes": None,
            },
        )

    assert response.status_code == 422


def test_missing_recovery_log_returns_not_found():
    with TestClient(app) as client:
        response = client.get("/recovery-logs/2026-09-19")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No existe un registro de recuperación para esta fecha."
    )