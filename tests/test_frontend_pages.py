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


def test_manifest_is_served_and_its_icons_exist():
    response = client.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/manifest+json"
    )

    manifest = response.json()

    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"

    sizes = {icon["sizes"] for icon in manifest["icons"]}
    purposes = {icon["purpose"] for icon in manifest["icons"]}

    assert {"192x192", "512x512"} <= sizes
    assert "maskable" in purposes

    for icon in manifest["icons"]:
        icon_response = client.get(icon["src"])

        assert icon_response.status_code == 200, icon["src"]
        assert icon_response.headers["content-type"] == "image/png"


def test_service_worker_is_served_from_the_root_with_full_scope():
    response = client.get("/sw.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.headers["service-worker-allowed"] == "/"
    # Una versión nueva debe llegar en la siguiente visita.
    assert response.headers["cache-control"] == "no-cache"


def test_service_worker_never_caches_api_responses():
    """Las respuestas de la API llevan datos de salud: no deben guardarse."""
    source = (FRONTEND / "sw.js").read_text(encoding="utf-8")

    # Solo se interceptan GET de la página de inicio y de /static/.
    assert 'request.method !== "GET"' in source
    assert 'url.pathname.startsWith("/static/")' in source
    assert "isCacheable(url)" in source

    for api_path in ("/auth", "/exports", "/restores", "/daily-logs"):
        assert f'"{api_path}' not in source


def test_every_page_links_the_manifest_and_loads_pwa_script():
    missing = []

    for page in FRONTEND.rglob("*.html"):
        html = page.read_text(encoding="utf-8")

        if (
            'rel="manifest"' not in html
            or 'href="/manifest.webmanifest"' not in html
            or 'src="/static/pwa.js"' not in html
        ):
            missing.append(page.relative_to(FRONTEND).as_posix())

    assert missing == []


def test_account_page_has_import_form_and_hidden_attribute_is_respected():
    html = (FRONTEND / "account" / "index.html").read_text(encoding="utf-8")

    for element_id in (
        "import-workouts-form", "import-workouts-file",
        "import-workouts-preview-button", "import-workouts-confirm-button",
        "import-workouts-source", "import-workouts-unit",
    ):
        assert f'id="{element_id}"' in html, element_id

    # El botón de confirmar empieza oculto; los botones tienen `display: flex`,
    # así que hace falta la regla global que respete el atributo `hidden`.
    css = (FRONTEND / "style.css").read_text(encoding="utf-8")

    assert "[hidden]" in css


def test_calendar_page_has_week_view_controls():
    html = (FRONTEND / "calendar" / "index.html").read_text(encoding="utf-8")

    for element_id in (
        "view-month-button", "view-week-button", "week-actions",
        "copy-from-previous-week-button", "copy-to-next-week-button",
        "calendar-weekdays",
    ):
        assert f'id="{element_id}"' in html, element_id

    # Los controles de copiar solo se muestran en la vista semanal.
    assert 'id="week-actions" class="calendar-week-actions" hidden' in html


def test_calendar_page_has_plan_summary_and_overdue_legend():
    html = (FRONTEND / "calendar" / "index.html").read_text(encoding="utf-8")

    assert 'id="plan-summary"' in html
    assert 'legend-dot overdue' in html
