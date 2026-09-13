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


def create_daily_log(
    client: TestClient,
    *,
    headers: dict[str, str],
    log_date: str,
    steps: int,
    notes: str | None = None,
) -> dict:
    response = client.post(
        "/daily-logs/",
        headers=headers,
        json={
            "date": log_date,
            "steps": steps,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_daily_logs_require_authentication():
    with TestClient(app) as client:
        response = client.get("/daily-logs/")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Se requiere un token de acceso."
    }


def test_user_can_create_get_update_and_delete_own_daily_log():
    log_date = "2026-08-10"

    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )

        created_log = create_daily_log(
            client,
            headers=headers,
            log_date=log_date,
            steps=8000,
            notes="Paseo por la tarde.",
        )

        get_response = client.get(
            f"/daily-logs/{log_date}",
            headers=headers,
        )
        update_response = client.put(
            f"/daily-logs/{log_date}",
            headers=headers,
            json={
                "steps": 10000,
                "notes": "Objetivo diario completado.",
            },
        )
        delete_response = client.delete(
            f"/daily-logs/{log_date}",
            headers=headers,
        )
        missing_response = client.get(
            f"/daily-logs/{log_date}",
            headers=headers,
        )

    assert created_log["date"] == log_date
    assert created_log["steps"] == 8000
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_log["id"]
    assert update_response.status_code == 200
    assert update_response.json()["steps"] == 10000
    assert update_response.json()["notes"] == "Objetivo diario completado."
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


def test_two_users_can_create_logs_for_the_same_date():
    log_date = "2026-08-11"

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

        ana_log = create_daily_log(
            client,
            headers=ana_headers,
            log_date=log_date,
            steps=8000,
        )
        bruno_log = create_daily_log(
            client,
            headers=bruno_headers,
            log_date=log_date,
            steps=12000,
        )

    assert ana_log["date"] == log_date
    assert ana_log["steps"] == 8000
    assert bruno_log["date"] == log_date
    assert bruno_log["steps"] == 12000
    assert ana_log["id"] != bruno_log["id"]


def test_user_cannot_create_duplicate_log_for_own_date():
    log_date = "2026-08-12"

    with TestClient(app) as client:
        headers = register_and_login(
            client,
            email="ana@example.com",
            display_name="Ana",
        )
        create_daily_log(
            client,
            headers=headers,
            log_date=log_date,
            steps=8000,
        )

        response = client.post(
            "/daily-logs/",
            headers=headers,
            json={
                "date": log_date,
                "steps": 9000,
                "notes": None,
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Ya existe un registro para esta fecha."
    }


def test_users_only_list_their_own_daily_logs():
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

        create_daily_log(
            client,
            headers=ana_headers,
            log_date="2026-08-13",
            steps=8000,
        )
        create_daily_log(
            client,
            headers=bruno_headers,
            log_date="2026-08-14",
            steps=12000,
        )

        ana_response = client.get(
            "/daily-logs/",
            headers=ana_headers,
        )
        bruno_response = client.get(
            "/daily-logs/",
            headers=bruno_headers,
        )

    assert ana_response.status_code == 200
    assert [log["date"] for log in ana_response.json()] == [
        "2026-08-13"
    ]
    assert bruno_response.status_code == 200
    assert [log["date"] for log in bruno_response.json()] == [
        "2026-08-14"
    ]


def test_user_cannot_access_another_users_daily_log():
    log_date = "2026-08-15"

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

        create_daily_log(
            client,
            headers=ana_headers,
            log_date=log_date,
            steps=8000,
        )

        get_response = client.get(
            f"/daily-logs/{log_date}",
            headers=bruno_headers,
        )
        update_response = client.put(
            f"/daily-logs/{log_date}",
            headers=bruno_headers,
            json={
                "steps": 10000,
                "notes": "No debe modificarse.",
            },
        )
        delete_response = client.delete(
            f"/daily-logs/{log_date}",
            headers=bruno_headers,
        )
        owner_response = client.get(
            f"/daily-logs/{log_date}",
            headers=ana_headers,
        )

    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404
    assert owner_response.status_code == 200
    assert owner_response.json()["steps"] == 8000