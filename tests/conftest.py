import atexit
import os
import tempfile

os.environ["FITNESS_TRACKER_TESTING"] = "1"
os.environ["FITNESS_TRACKER_JWT_SECRET"] = (
    "test-only-secret-that-is-at-least-32-bytes-long"
)
# Los tests registran usuarios sin código; los de invitaciones lo cambian.
os.environ["FITNESS_TRACKER_REGISTRATION_MODE"] = "open"
os.environ["FITNESS_TRACKER_ACCESS_TOKEN_MINUTES"] = "60"

# Los tests vacían las tablas: NUNCA deben apuntar a una base real. Se usa
# FITNESS_TRACKER_TEST_DATABASE_URL (p. ej. el servicio de PostgreSQL de CI) o,
# si no existe, un PostgreSQL temporal y local que levanta `pgserver`.
os.environ.pop("FITNESS_TRACKER_DATABASE_URL", None)
_test_database_url = os.environ.get("FITNESS_TRACKER_TEST_DATABASE_URL")

if not _test_database_url:
    try:
        import pgserver
    except ImportError as error:  # pragma: no cover
        raise RuntimeError(
            "Define FITNESS_TRACKER_TEST_DATABASE_URL o instala "
            "requirements-dev.txt (pgserver)."
        ) from error

    _postgres = pgserver.get_server(
        tempfile.mkdtemp(prefix="fitness-tracker-pg-"),
        cleanup_mode="stop",
    )
    atexit.register(_postgres.cleanup)
    _test_database_url = _postgres.get_uri()

os.environ["FITNESS_TRACKER_DATABASE_URL"] = _test_database_url

import pytest
from fastapi.testclient import TestClient

from app.db import get_connection, initialize_database
from app.schema import TABLES
from app.rate_limit import reset_rate_limits


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()
    reset_rate_limits()

    tables = ", ".join(TABLES)

    with get_connection() as connection:
        connection.execute(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")

    yield


def register_and_login(
    client: TestClient,
    *,
    email: str = "test@example.com",
    display_name: str = "Test User",
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