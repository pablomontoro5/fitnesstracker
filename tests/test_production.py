import importlib
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app as default_app
from tests.conftest import register_and_login


REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"
LOGIN_HTML = (
    Path(__file__).resolve().parent.parent / "app/frontend/login/index.html"
)


@pytest.fixture
def reload_app(monkeypatch):
    def build(value):
        if value is None:
            monkeypatch.delenv("FITNESS_TRACKER_ENABLE_DOCS", raising=False)
        else:
            monkeypatch.setenv("FITNESS_TRACKER_ENABLE_DOCS", value)

        return importlib.reload(main_module).app

    yield build
    monkeypatch.delenv("FITNESS_TRACKER_ENABLE_DOCS", raising=False)
    importlib.reload(main_module)


def test_docs_are_disabled_by_default(reload_app):
    client = TestClient(reload_app(None))

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404

    assert client.get("/health").status_code == 200


def test_docs_can_be_enabled_explicitly(reload_app):
    client = TestClient(reload_app("1"))

    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_requirements_are_pinned():
    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    assert lines
    assert all("==" in line for line in lines), lines


def test_login_password_field_has_no_minlength():
    html = LOGIN_HTML.read_text()
    start = html.index('id="login-password"')
    field = html[start : html.index("/>", start)]

    assert "minlength" not in field


def test_security_events_are_logged_without_secrets(caplog):
    client = TestClient(default_app)
    caplog.set_level(logging.INFO, logger="fitness_tracker")
    logger = logging.getLogger("fitness_tracker")
    logger.propagate = True

    try:
        headers = register_and_login(client, email="logs@example.com")
        client.post(
            "/auth/login",
            json={"email": "logs@example.com", "password": "incorrecta-123"},
        )
    finally:
        logger.propagate = False

    text = caplog.text

    assert "Login correcto" in text
    assert "Login fallido" in text
    assert "logs@example.com" not in text
    assert "password-segura-123" not in text
    assert "incorrecta-123" not in text
    assert headers["Authorization"].split()[-1] not in text
