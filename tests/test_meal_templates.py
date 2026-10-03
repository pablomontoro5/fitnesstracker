"""Plantillas de comida contra la base de datos real (esquema de db.py)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


client = TestClient(app)


@pytest.fixture
def owner():
    return register_and_login(client, email="owner@example.com")


@pytest.fixture
def other():
    return register_and_login(client, email="other@example.com")


def create_food(headers, name, calories, protein, carbs, fat):
    response = client.post(
        "/food-library/",
        json={
            "name": name,
            "calories_per_100g": calories,
            "protein_per_100g": protein,
            "carbs_per_100g": carbs,
            "fat_per_100g": fat,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_template(headers, name="Desayuno"):
    response = client.post(
        "/meal-templates/",
        json={"name": name, "notes": "Habitual"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_get_and_update(owner):
    created = create_template(owner)
    template_id = created["id"]

    assert created["items"] == []
    assert created["calories"] == 0
    assert client.get(
        f"/meal-templates/{template_id}", headers=owner
    ).json() == created
    assert [
        item["id"] for item in client.get("/meal-templates/", headers=owner).json()
    ] == [template_id]

    updated = client.put(
        f"/meal-templates/{template_id}",
        json={"name": "Merienda", "notes": None},
        headers=owner,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Merienda"
    assert updated.json()["notes"] is None


def test_add_update_and_delete_item_recalculates_totals(owner):
    oats = create_food(owner, "Avena", 400, 20, 60, 10)
    milk = create_food(owner, "Leche", 50, 3, 5, 2)
    template_id = create_template(owner)["id"]

    added = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": oats, "grams": 50},
        headers=owner,
    )
    assert added.status_code == 201, added.text
    body = added.json()
    item_id = body["items"][0]["id"]
    assert body["items"][0]["name"] == "Avena"
    assert body["items"][0]["grams"] == 50
    assert body["calories"] == pytest.approx(200)
    assert body["protein"] == pytest.approx(10)
    assert body["carbs"] == pytest.approx(30)
    assert body["fat"] == pytest.approx(5)

    # Solo gramos.
    heavier = client.put(
        f"/meal-templates/{template_id}/items/{item_id}",
        json={"grams": 100},
        headers=owner,
    )
    assert heavier.status_code == 200, heavier.text
    assert heavier.json()["calories"] == pytest.approx(400)

    # Cambiar de alimento.
    changed = client.put(
        f"/meal-templates/{template_id}/items/{item_id}",
        json={"food_id": milk, "grams": 200},
        headers=owner,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["items"][0]["name"] == "Leche"
    assert changed.json()["calories"] == pytest.approx(100)
    assert changed.json()["protein"] == pytest.approx(6)
    assert changed.json()["carbs"] == pytest.approx(10)
    assert changed.json()["fat"] == pytest.approx(4)

    deleted = client.delete(
        f"/meal-templates/{template_id}/items/{item_id}", headers=owner
    )
    assert deleted.status_code == 204, deleted.text
    assert client.get(
        f"/meal-templates/{template_id}", headers=owner
    ).json()["items"] == []


def test_items_keep_their_order_after_deleting_one(owner):
    food = create_food(owner, "Avena", 400, 20, 60, 10)
    template_id = create_template(owner)["id"]
    ids = []

    for grams in (10, 20, 30):
        body = client.post(
            f"/meal-templates/{template_id}/items",
            json={"food_id": food, "grams": grams},
            headers=owner,
        ).json()
        ids.append(body["items"][-1]["id"])

    client.delete(f"/meal-templates/{template_id}/items/{ids[1]}", headers=owner)
    added = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": food, "grams": 40},
        headers=owner,
    )

    assert added.status_code == 201, added.text
    assert [item["grams"] for item in added.json()["items"]] == [10, 30, 40]


def test_items_keep_a_copy_of_the_food_when_the_library_changes(owner):
    food = create_food(owner, "Avena", 400, 20, 60, 10)
    template_id = create_template(owner)["id"]
    client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": food, "grams": 50},
        headers=owner,
    )

    client.put(
        f"/food-library/{food}",
        json={
            "name": "Avena integral",
            "calories_per_100g": 100,
            "protein_per_100g": 1,
            "carbs_per_100g": 1,
            "fat_per_100g": 1,
        },
        headers=owner,
    )
    assert client.delete(f"/food-library/{food}", headers=owner).status_code == 204

    template = client.get(f"/meal-templates/{template_id}", headers=owner).json()

    assert template["items"][0]["name"] == "Avena"
    assert template["calories"] == pytest.approx(200)


def test_delete_template_removes_items(owner):
    food = create_food(owner, "Avena", 400, 20, 60, 10)
    template_id = create_template(owner)["id"]
    assert client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": food, "grams": 100},
        headers=owner,
    ).status_code == 201

    assert client.delete(
        f"/meal-templates/{template_id}", headers=owner
    ).status_code == 204
    assert client.get(
        f"/meal-templates/{template_id}", headers=owner
    ).status_code == 404
    assert client.get("/meal-templates/", headers=owner).json() == []


def test_users_cannot_access_each_others_templates(owner, other):
    private_food = create_food(other, "Privado", 100, 10, 10, 2)
    template_id = create_template(owner)["id"]

    assert client.get("/meal-templates/", headers=other).json() == []
    assert client.get(
        f"/meal-templates/{template_id}", headers=other
    ).status_code == 404
    assert client.put(
        f"/meal-templates/{template_id}",
        json={"name": "Intrusión", "notes": None},
        headers=other,
    ).status_code == 404
    assert client.delete(
        f"/meal-templates/{template_id}", headers=other
    ).status_code == 404
    assert client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": private_food, "grams": 100},
        headers=other,
    ).status_code == 404
    assert client.get(
        f"/meal-templates/{template_id}", headers=owner
    ).status_code == 200


def test_cannot_use_another_users_food(owner, other):
    private_food = create_food(other, "Privado", 100, 10, 10, 2)
    template_id = create_template(owner)["id"]

    response = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": private_food, "grams": 100},
        headers=owner,
    )

    assert response.status_code == 404, response.text
    assert client.get(
        f"/meal-templates/{template_id}", headers=owner
    ).json()["items"] == []


@pytest.mark.parametrize("grams", [0, -1])
def test_grams_must_be_positive(owner, grams):
    food = create_food(owner, "Avena", 400, 20, 60, 10)
    template_id = create_template(owner)["id"]

    response = client.post(
        f"/meal-templates/{template_id}/items",
        json={"food_id": food, "grams": grams},
        headers=owner,
    )

    assert response.status_code == 422, response.text


def test_blank_name_and_missing_resources(owner):
    assert client.post(
        "/meal-templates/", json={"name": "   ", "notes": None}, headers=owner
    ).status_code == 422
    assert client.get("/meal-templates/99999", headers=owner).status_code == 404
    assert client.delete("/meal-templates/99999", headers=owner).status_code == 404

    template_id = create_template(owner)["id"]

    assert client.put(
        f"/meal-templates/{template_id}/items/99999",
        json={"grams": 100},
        headers=owner,
    ).status_code == 404
    assert client.delete(
        f"/meal-templates/{template_id}/items/99999", headers=owner
    ).status_code == 404


def test_requires_authentication():
    assert client.get("/meal-templates/").status_code == 401
