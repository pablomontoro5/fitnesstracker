import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.routers import meal_templates


@pytest.fixture
def environment(tmp_path, monkeypatch):
    database = tmp_path / "meal_templates_test.sqlite3"

    def connection():
        db = sqlite3.connect(database)
        db.row_factory = sqlite3.Row
        return db

    with connection() as db:
        db.executescript(
            """
            CREATE TABLE food_library (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                calories_per_100g REAL NOT NULL,
                protein_per_100g REAL NOT NULL,
                carbs_per_100g REAL NOT NULL,
                fat_per_100g REAL NOT NULL
            );
            CREATE TABLE meal_templates (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                notes TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE meal_template_items (
                id INTEGER PRIMARY KEY,
                template_id INTEGER NOT NULL,
                food_id INTEGER NOT NULL,
                grams REAL NOT NULL
            );
            """
        )
        db.executemany(
            """INSERT INTO food_library
               (id, user_id, name, calories_per_100g, protein_per_100g,
                carbs_per_100g, fat_per_100g) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (1, 1, "Avena", 400, 20, 60, 10),
                (2, 1, "Leche", 50, 3, 5, 2),
                (3, 2, "Alimento privado", 100, 10, 10, 2),
            ],
        )

    monkeypatch.setattr(meal_templates, "get_connection", connection)
    user = SimpleNamespace(id=1)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield client, user
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def create_template(client, name="Desayuno"):
    response = client.post(
        "/meal-templates/", json={"name": name, "notes": "Habitual"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_get_and_update(environment):
    client, _ = environment
    created = create_template(client)
    template_id = created["id"]
    assert created["items"] == []
    assert created["calories"] == 0
    assert client.get(f"/meal-templates/{template_id}").json() == created
    assert [item["id"] for item in client.get("/meal-templates/").json()] == [template_id]

    updated = client.put(
        f"/meal-templates/{template_id}",
        json={"name": "Merienda", "notes": None},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Merienda"
    assert updated.json()["notes"] is None


def test_add_update_and_delete_item_recalculates_totals(environment):
    client, _ = environment
    template_id = create_template(client)["id"]
    added = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": 1, "grams": 50},
    )
    assert added.status_code == 201, added.text
    body = added.json()
    item_id = body["items"][0]["id"]
    assert body["items"][0]["name"] == "Avena"
    assert body["calories"] == pytest.approx(200)
    assert body["protein"] == pytest.approx(10)
    assert body["carbs"] == pytest.approx(30)
    assert body["fat"] == pytest.approx(5)

    changed = client.put(
        f"/meal-templates/{template_id}/items/{item_id}",
        json={"food_id": 2, "grams": 200},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["calories"] == pytest.approx(100)
    assert changed.json()["protein"] == pytest.approx(6)
    assert changed.json()["carbs"] == pytest.approx(10)
    assert changed.json()["fat"] == pytest.approx(4)

    deleted = client.delete(f"/meal-templates/{template_id}/items/{item_id}")
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/meal-templates/{template_id}").json()["items"] == []


def test_delete_template_removes_items(environment):
    client, _ = environment
    template_id = create_template(client)["id"]
    assert client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": 1, "grams": 100},
    ).status_code == 201
    assert client.delete(f"/meal-templates/{template_id}").status_code == 204
    assert client.get(f"/meal-templates/{template_id}").status_code == 404
    assert client.get("/meal-templates/").json() == []


def test_users_cannot_access_each_others_templates(environment):
    client, user = environment
    template_id = create_template(client)["id"]
    user.id = 2
    assert client.get("/meal-templates/").json() == []
    assert client.get(f"/meal-templates/{template_id}").status_code == 404
    assert client.put(
        f"/meal-templates/{template_id}",
        json={"name": "Intrusión", "notes": None},
    ).status_code == 404
    assert client.delete(f"/meal-templates/{template_id}").status_code == 404
    assert client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": 3, "grams": 100},
    ).status_code == 404
    user.id = 1
    assert client.get(f"/meal-templates/{template_id}").status_code == 200


def test_cannot_use_another_users_food(environment):
    client, _ = environment
    template_id = create_template(client)["id"]
    response = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": 3, "grams": 100},
    )
    assert response.status_code == 404, response.text
    assert client.get(f"/meal-templates/{template_id}").json()["items"] == []


@pytest.mark.parametrize("grams", [0, -1])
def test_grams_must_be_positive(environment, grams):
    client, _ = environment
    template_id = create_template(client)["id"]
    response = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": 1, "grams": grams},
    )
    assert response.status_code == 422, response.text


def test_blank_name_and_missing_resources(environment):
    client, _ = environment
    assert client.post(
        "/meal-templates/", json={"name": "   ", "notes": None}
    ).status_code == 422
    assert client.get("/meal-templates/99999").status_code == 404
    assert client.delete("/meal-templates/99999").status_code == 404
    template_id = create_template(client)["id"]
    assert client.put(
        f"/meal-templates/{template_id}/items/99999",
        json={"food_id": 1, "grams": 100},
    ).status_code == 404
    assert client.delete(
        f"/meal-templates/{template_id}/items/99999"
    ).status_code == 404