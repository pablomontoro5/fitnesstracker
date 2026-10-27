import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import ANGULAR_DIR
from app.main import app as real_app
from app.spa import SinglePageApp


@pytest.fixture
def spa_client(tmp_path):
    (tmp_path / "index.html").write_text("<app-root>INICIO</app-root>", encoding="utf-8")
    (tmp_path / "main-ABC123.js").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")

    spa = FastAPI()
    spa.mount("/app", SinglePageApp(directory=tmp_path), name="angular")

    return TestClient(spa)


def test_the_root_of_the_app_serves_index_html(spa_client):
    response = spa_client.get("/app/")

    assert response.status_code == 200
    assert "INICIO" in response.text


def test_screen_routes_without_a_file_fall_back_to_index_html(spa_client):
    """Recargar /app/privacidad debe abrir la app y dejar a Angular elegir."""
    for path in ("/app/privacidad", "/app/calendario/semana", "/app/a/b/c"):
        response = spa_client.get(path)

        assert response.status_code == 200, path
        assert "INICIO" in response.text, path


def test_existing_files_are_served_as_they_are(spa_client):
    script = spa_client.get("/app/main-ABC123.js")

    assert script.status_code == 200
    assert "console.log" in script.text
    assert "INICIO" not in script.text
    assert spa_client.get("/app/logo.png").content == b"\x89PNG"


def test_missing_files_with_an_extension_are_404_not_index_html(spa_client):
    """Si falta un .js, el navegador no debe recibir HTML y fallar de forma
    confusa: tiene que ser un 404 claro."""
    for path in ("/app/main-OTRO.js", "/app/falta.png", "/app/estilos.css"):
        assert spa_client.get(path).status_code == 404, path


def test_the_current_app_is_not_affected_by_the_angular_one():
    client = TestClient(real_app)

    assert client.get("/").status_code == 200
    assert client.get("/static/login/").status_code == 200
    assert client.get("/health").status_code in (200, 503)


@pytest.mark.skipif(
    not (ANGULAR_DIR / "index.html").is_file(),
    reason="Angular no está compilado (ng build) en este entorno.",
)
def test_the_real_app_serves_the_compiled_angular_build():
    client = TestClient(real_app)

    index = client.get("/app/")
    deep_link = client.get("/app/privacidad")

    assert index.status_code == 200
    assert '<base href="/app/">' in index.text
    assert deep_link.status_code == 200
    assert "<app-root>" in deep_link.text
