import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import exports


def test_download_fitness_tracker_export_returns_json_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(exports, "EXPORTS_DIR", tmp_path)

    with TestClient(app) as client:
        response = client.get("/exports/fitness-tracker.json")

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

    created_exports = list(
        tmp_path.glob("fitness_tracker_export_*.json")
    )

    assert len(created_exports) == 1
    assert json.loads(created_exports[0].read_text(encoding="utf-8")) == (
        export_data
    )