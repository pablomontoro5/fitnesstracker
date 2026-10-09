import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


FRONTEND = Path(__file__).resolve().parent.parent / "app" / "frontend"
client = TestClient(app)


def internal_links(html_path: Path) -> set[str]:
    html = html_path.read_text(encoding="utf-8")

    return {
        href.split("#")[0].split("?")[0]
        for href in re.findall(r'href="(/[^"]*)"', html)
    }


def test_every_internal_link_in_the_frontend_resolves():
    """Evita enlaces rotos como el del calendario, que daba 404."""
    broken = []

    for page in FRONTEND.rglob("*.html"):
        for link in internal_links(page):
            response = client.get(link)

            if response.status_code != 200:
                broken.append((page.relative_to(FRONTEND).as_posix(), link))

    assert broken == []


def test_privacy_notice_is_served_and_linked_from_signup_and_account():
    response = client.get("/static/privacy/")

    assert response.status_code == 200
    assert "Aviso de privacidad" in response.text
    # Hasta que se rellenen, los huecos del responsable deben ser visibles.
    assert "[EMAIL DE CONTACTO]" in response.text

    for page in ("login", "account"):
        html = (FRONTEND / page / "index.html").read_text(encoding="utf-8")
        assert 'href="/static/privacy/"' in html, page
