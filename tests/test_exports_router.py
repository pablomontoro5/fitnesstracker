import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import exports
from tests.conftest import register_and_login


def test_export_requires_authentication(tmp_path, monkeypatch):
    monkeypatch.setattr(exports, "EXPORTS_DIR", tmp_path)

    with TestClient(app) as client:
        response = client.get("/exports/fitness-tracker.json")

    assert response.status_code == 401
    assert list(tmp_path.iterdir()) == []


def test_download_fitness_tracker_export_returns_json_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(exports, "EXPORTS_DIR", tmp_path)

    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.get(
            "/exports/fitness-tracker.json",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/json"
    )

    content_disposition = response.headers["content-disposition"]

    assert "attachment" in content_disposition
    assert "fitness_tracker_export_" in content_disposition
    assert content_disposition.endswith(".json\"")

    export_data = response.json()

    assert "exported_at" in export_data
    assert export_data["daily_logs"] == []
    assert export_data["body_metrics"] == []
    assert export_data["workout_sessions"] == []
    assert export_data["runs"] == []
    assert export_data["nutrition_days"] == []

    # El fichero temporal se borra tras entregarlo.
    assert list(tmp_path.glob("fitness_tracker_export_*.json")) == []


def test_export_only_contains_the_authenticated_users_data(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(exports, "EXPORTS_DIR", tmp_path)

    with TestClient(app) as client:
        alice = register_and_login(client, email="alice@example.com")
        bob = register_and_login(client, email="bob@example.com")

        client.post(
            "/daily-logs/",
            headers=alice,
            json={"date": "2026-09-01", "steps": 1, "notes": "NOTA-ALICE"},
        )
        client.post(
            "/runs/",
            headers=bob,
            json={
                "date": "2026-09-02",
                "distance_km": 5,
                "duration_seconds": 1500,
                "notes": "NOTA-BOB",
            },
        )

        alice_export = client.get(
            "/exports/fitness-tracker.json", headers=alice,
        )
        bob_export = client.get(
            "/exports/fitness-tracker.json", headers=bob,
        )

    assert "NOTA-ALICE" in alice_export.text
    assert "NOTA-BOB" not in alice_export.text
    assert "NOTA-BOB" in bob_export.text
    assert "NOTA-ALICE" not in bob_export.text
    assert json.loads(bob_export.text)["daily_logs"] == []
