from fastapi.testclient import TestClient

from app.main import app


def register_and_login(
    client: TestClient,
    *,
    email: str,
    display_name: str,
) -> dict[str, str]:
    password = "password-segura-123"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": display_name,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }


def create_recovery_log(
    client: TestClient,
    *,
    headers: dict[str, str],
    log_date: str = "2026-09-09",
    sleep_minutes: int | None = 450,
    sleep_quality: int | None = 4,
    is_rest_day: bool = False,
    notes: str | None = "Movilidad suave.",
) -> dict:
    response = client.post(
        "/recovery-logs/",
        headers=headers,
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


def test_recovery_logs_require_authentication():
    with TestClient(app) as client:
        response = client.get("/recovery-logs/")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Se requiere un token de acceso."
    }


def test_user_can_create_recovery_log_and_rest_day_without_sleep():
    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )

        recovery_log = create_recovery_log(client, headers=headers)

        rest_day_response = client.post(
            "/recovery-logs/",
            headers=headers,
            json={
                "date": "2026-09-10",
                "sleep_minutes": None,
                "sleep_quality": None,
                "is_rest_day": True,
                "notes": None,
            },
        )

    assert recovery_log["date"] == "2026-09-09"
    assert recovery_log["sleep_minutes"] == 450
    assert rest_day_response.status_code == 201
    assert rest_day_response.json()["sleep_minutes"] is None
    assert rest_day_response.json()["is_rest_day"] is True


def test_two_users_can_create_recovery_logs_for_same_date():
    log_date = "2026-09-09"

    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno@example.com",
            display_name="Bruno",
        )

        ana_log = create_recovery_log(
            client,
            headers=ana_headers,
            log_date=log_date,
            sleep_minutes=450,
        )
        bruno_log = create_recovery_log(
            client,
            headers=bruno_headers,
            log_date=log_date,
            sleep_minutes=510,
        )

    assert ana_log["id"] != bruno_log["id"]
    assert ana_log["sleep_minutes"] == 450
    assert bruno_log["sleep_minutes"] == 510


def test_user_cannot_create_duplicate_recovery_log_for_own_date():
    log_date = "2026-09-09"

    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )
        create_recovery_log(
            client,
            headers=headers,
            log_date=log_date,
        )

        response = client.post(
            "/recovery-logs/",
            headers=headers,
            json={
                "date": log_date,
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


def test_users_only_list_their_own_recovery_logs():
    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno@example.com",
            display_name="Bruno",
        )

        create_recovery_log(
            client,
            headers=ana_headers,
            log_date="2026-09-09",
        )
        create_recovery_log(
            client,
            headers=bruno_headers,
            log_date="2026-09-10",
        )

        ana_response = client.get(
            "/recovery-logs/",
            headers=ana_headers,
        )
        bruno_response = client.get(
            "/recovery-logs/",
            headers=bruno_headers,
        )

    assert ana_response.status_code == 200
    assert [log["date"] for log in ana_response.json()] == [
        "2026-09-09"
    ]
    assert bruno_response.status_code == 200
    assert [log["date"] for log in bruno_response.json()] == [
        "2026-09-10"
    ]


def test_user_cannot_access_another_users_recovery_log():
    log_date = "2026-09-09"

    with TestClient(app) as client:
        ana_headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )
        bruno_headers = register_and_login(
            client,
            email="bruno@example.com",
            display_name="Bruno",
        )

        create_recovery_log(
            client,
            headers=ana_headers,
            log_date=log_date,
        )

        get_response = client.get(
            f"/recovery-logs/{log_date}",
            headers=bruno_headers,
        )
        update_response = client.put(
            f"/recovery-logs/{log_date}",
            headers=bruno_headers,
            json={
                "sleep_minutes": 480,
                "sleep_quality": 5,
                "is_rest_day": True,
                "notes": "No debe modificarse.",
            },
        )
        delete_response = client.delete(
            f"/recovery-logs/{log_date}",
            headers=bruno_headers,
        )
        owner_response = client.get(
            f"/recovery-logs/{log_date}",
            headers=ana_headers,
        )

    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404
    assert owner_response.status_code == 200
    assert owner_response.json()["sleep_minutes"] == 450


def test_recovery_log_rejects_invalid_values():
    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )

        invalid_sleep_response = client.post(
            "/recovery-logs/",
            headers=headers,
            json={
                "date": "2026-09-09",
                "sleep_minutes": 1441,
                "sleep_quality": 4,
                "is_rest_day": False,
                "notes": None,
            },
        )
        invalid_quality_response = client.post(
            "/recovery-logs/",
            headers=headers,
            json={
                "date": "2026-09-10",
                "sleep_minutes": 480,
                "sleep_quality": 6,
                "is_rest_day": False,
                "notes": None,
            },
        )

    assert invalid_sleep_response.status_code == 422
    assert invalid_quality_response.status_code == 422