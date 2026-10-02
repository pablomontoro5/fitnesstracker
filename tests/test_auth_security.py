from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import cli
from app.db import get_connection
from app.invitations import (
    REGISTRATION_MODE_ENV,
    create_invitation,
    get_registration_mode,
)
from app.main import app
from app.rate_limit import RateLimiter
from app.security import JWT_SECRET_ENV, get_jwt_secret


PASSWORD = "password-segura-123"


def register_payload(email: str, invite_code: str | None = None) -> dict:
    payload = {
        "email": email,
        "display_name": "Usuario",
        "password": PASSWORD,
    }

    if invite_code is not None:
        payload["invite_code"] = invite_code

    return payload


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def new_invitation(**kwargs) -> str:
    with get_connection() as connection:
        code, _ = create_invitation(connection, **kwargs)

    return code


# --------------------------------------------------------------- JWT secret


def test_jwt_secret_shorter_than_32_bytes_is_rejected(monkeypatch):
    monkeypatch.setenv(JWT_SECRET_ENV, "Pablo2204")

    with pytest.raises(RuntimeError, match="al menos 32 bytes"):
        get_jwt_secret()


def test_server_refuses_to_start_with_a_weak_jwt_secret(monkeypatch):
    monkeypatch.setenv(JWT_SECRET_ENV, "corta")

    with pytest.raises(RuntimeError, match="al menos 32 bytes"):
        with TestClient(app):
            pass


def test_server_refuses_to_start_with_an_unknown_registration_mode(
    monkeypatch,
):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "abierto")

    with pytest.raises(RuntimeError, match="'invite' u 'open'"):
        with TestClient(app):
            pass


def test_registration_mode_defaults_to_invite(monkeypatch):
    monkeypatch.delenv(REGISTRATION_MODE_ENV, raising=False)

    assert get_registration_mode() == "invite"


# ------------------------------------------------------------- RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_rate_limiter_blocks_after_max_attempts_and_expires():
    clock = FakeClock()
    limiter = RateLimiter(max_attempts=3, window_seconds=60, clock=clock)

    for _ in range(3):
        assert limiter.retry_after("k") == 0
        limiter.record("k")

    assert limiter.retry_after("k") == 60

    clock.now += 45
    assert limiter.retry_after("k") == 15

    clock.now += 15
    assert limiter.retry_after("k") == 0


def test_rate_limiter_keys_are_independent_and_resettable():
    limiter = RateLimiter(max_attempts=1, window_seconds=60)

    limiter.record("a")

    assert limiter.retry_after("a") > 0
    assert limiter.retry_after("b") == 0

    limiter.reset("a")

    assert limiter.retry_after("a") == 0


def test_rate_limiter_memory_is_bounded(monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(rate_limit, "MAX_TRACKED_KEYS", 5)
    limiter = RateLimiter(max_attempts=3, window_seconds=60)

    for index in range(50):
        limiter.record(f"key-{index}")

    assert len(limiter._attempts) <= 5


# ------------------------------------------------------------ login limits


def test_login_is_blocked_after_five_failures_even_with_right_password():
    with TestClient(app) as client:
        client.post("/auth/register", json=register_payload("a@example.com"))

        for _ in range(5):
            assert login(client, "a@example.com", "mala-contraseña-1").status_code == 401

        blocked = login(client, "a@example.com")

        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) > 0
        assert "Demasiados intentos" in blocked.json()["detail"]


def test_successful_login_resets_the_failure_counter():
    with TestClient(app) as client:
        client.post("/auth/register", json=register_payload("a@example.com"))

        for _ in range(4):
            assert login(client, "a@example.com", "mala-contraseña-1").status_code == 401

        assert login(client, "a@example.com").status_code == 200

        for _ in range(4):
            assert login(client, "a@example.com", "mala-contraseña-1").status_code == 401

        assert login(client, "a@example.com").status_code == 200


def test_login_failures_for_one_account_do_not_block_another():
    with TestClient(app) as client:
        client.post("/auth/register", json=register_payload("a@example.com"))
        client.post("/auth/register", json=register_payload("b@example.com"))

        for _ in range(5):
            login(client, "a@example.com", "mala-contraseña-1")

        assert login(client, "a@example.com").status_code == 429
        assert login(client, "b@example.com").status_code == 200


def test_login_is_blocked_per_ip_when_spraying_many_emails():
    with TestClient(app) as client:
        for index in range(20):
            response = login(client, f"nadie{index}@example.com", "mala-contraseña-1")
            assert response.status_code == 401

        blocked = login(client, "otro@example.com", "mala-contraseña-1")

        assert blocked.status_code == 429


# ---------------------------------------------------------- register limits


def test_register_is_limited_per_ip():
    with TestClient(app) as client:
        for _ in range(10):
            client.post("/auth/register", json=register_payload("a@example.com"))

        blocked = client.post(
            "/auth/register",
            json=register_payload("b@example.com"),
        )

        assert blocked.status_code == 429


# -------------------------------------------------------------- invitations


def test_registration_without_code_is_forbidden_in_invite_mode(monkeypatch):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "invite")

    with TestClient(app) as client:
        missing = client.post("/auth/register", json=register_payload("a@example.com"))
        wrong = client.post(
            "/auth/register",
            json=register_payload("a@example.com", "codigo-inventado"),
        )

        assert missing.status_code == 403
        assert wrong.status_code == 403
        assert missing.json() == wrong.json()
        assert login(client, "a@example.com").status_code == 401


def test_valid_invitation_allows_registration_once(monkeypatch):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "invite")

    with TestClient(app) as client:
        code = new_invitation()

        first = client.post(
            "/auth/register",
            json=register_payload("a@example.com", code),
        )
        reused = client.post(
            "/auth/register",
            json=register_payload("b@example.com", code),
        )

        assert first.status_code == 201
        assert reused.status_code == 403
        assert login(client, "a@example.com").status_code == 200
        assert login(client, "b@example.com").status_code == 401

        with get_connection() as connection:
            row = connection.execute(
                "SELECT used_at, used_by_user_id FROM invitations"
            ).fetchone()

        assert row["used_at"] is not None
        assert row["used_by_user_id"] == first.json()["id"]


def test_expired_invitation_is_rejected(monkeypatch):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "invite")

    with TestClient(app) as client:
        code = new_invitation(
            now=datetime.now(timezone.utc) - timedelta(days=8),
        )

        response = client.post(
            "/auth/register",
            json=register_payload("a@example.com", code),
        )

        assert response.status_code == 403


def test_failed_registration_does_not_consume_the_invitation(monkeypatch):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "open")

    with TestClient(app) as client:
        client.post("/auth/register", json=register_payload("a@example.com"))

    monkeypatch.setenv(REGISTRATION_MODE_ENV, "invite")

    with TestClient(app) as client:
        code = new_invitation()

        duplicate = client.post(
            "/auth/register",
            json=register_payload("a@example.com", code),
        )
        retry = client.post(
            "/auth/register",
            json=register_payload("b@example.com", code),
        )

        assert duplicate.status_code == 409
        assert retry.status_code == 201


def test_invitation_codes_are_stored_hashed():
    code = new_invitation()

    with get_connection() as connection:
        stored = connection.execute(
            "SELECT code_hash FROM invitations"
        ).fetchone()["code_hash"]

    assert code not in stored
    assert len(stored) == 64


def test_open_mode_does_not_require_a_code(monkeypatch):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "open")

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json=register_payload("a@example.com"),
        )

        assert response.status_code == 201


# ---------------------------------------------------------------------- CLI


def test_cli_creates_an_invitation_that_works(monkeypatch, capsys):
    monkeypatch.setenv(REGISTRATION_MODE_ENV, "invite")

    assert cli.main(["create-invite", "--days", "3"]) == 0

    output = capsys.readouterr().out
    code = output.splitlines()[0].split(": ", 1)[1].strip()

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json=register_payload("a@example.com", code),
        )

        assert response.status_code == 201


def test_cli_rejects_a_non_positive_number_of_days():
    with pytest.raises(SystemExit):
        cli.main(["create-invite", "--days", "0"])
