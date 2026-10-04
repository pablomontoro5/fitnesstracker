"""Biblioteca de alimentos contra la base de datos real."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


class CurrentUser:
    """Cambia la cuenta activa del cliente: user.id = 1 o 2."""

    def __init__(self, client, accounts):
        self._client = client
        self._accounts = accounts
        self.id = 1

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        self._client.headers.clear()
        self._client.headers.update(self._accounts[value])


@pytest.fixture
def environment():
    with TestClient(app) as client:
        accounts = {
            1: register_and_login(client, email="uno@example.com"),
            2: register_and_login(client, email="dos@example.com"),
        }
        yield client, CurrentUser(client, accounts)


@pytest.fixture
def sample_food():
    return {
        "name": "Avena",
        "calories_per_100g": 389,
        "protein_per_100g": 16.9,
        "carbs_per_100g": 66.3,
        "fat_per_100g": 6.9,
        "notes": "Copos de avena",
    }


def test_create_and_get_food(environment, sample_food):
    client, _ = environment
    created = client.post("/food-library/", json=sample_food)
    assert created.status_code == 201, created.text
    item = created.json()
    assert isinstance(item["id"], int)
    for key, value in sample_food.items():
        assert item[key] == value

    fetched = client.get(f"/food-library/{item['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json() == item


def test_list_only_current_users_food(environment, sample_food):
    client, user = environment
    first = client.post("/food-library/", json=sample_food)
    assert first.status_code == 201, first.text

    user.id = 2
    second = client.post(
        "/food-library/", json={**sample_food, "name": "Arroz"}
    )
    assert second.status_code == 201, second.text
    assert [item["id"] for item in client.get("/food-library/").json()] == [
        second.json()["id"]
    ]

    user.id = 1
    assert [item["id"] for item in client.get("/food-library/").json()] == [
        first.json()["id"]
    ]


def test_update_food(environment, sample_food):
    client, _ = environment
    created = client.post("/food-library/", json=sample_food)
    assert created.status_code == 201, created.text
    food_id = created.json()["id"]
    updated_food = {**sample_food, "name": "Avena integral", "notes": None}

    updated = client.put(f"/food-library/{food_id}", json=updated_food)
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Avena integral"
    assert updated.json()["notes"] is None
    assert client.get(f"/food-library/{food_id}").json() == updated.json()


def test_delete_food(environment, sample_food):
    client, _ = environment
    created = client.post("/food-library/", json=sample_food)
    assert created.status_code == 201, created.text
    food_id = created.json()["id"]

    deleted = client.delete(f"/food-library/{food_id}")
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/food-library/{food_id}").status_code == 404
    assert client.get("/food-library/").json() == []


def test_other_user_cannot_read_update_or_delete(environment, sample_food):
    client, user = environment
    created = client.post("/food-library/", json=sample_food)
    assert created.status_code == 201, created.text
    food_id = created.json()["id"]

    user.id = 2
    assert client.get(f"/food-library/{food_id}").status_code == 404
    assert client.put(f"/food-library/{food_id}", json=sample_food).status_code == 404
    assert client.delete(f"/food-library/{food_id}").status_code == 404

    user.id = 1
    assert client.get(f"/food-library/{food_id}").status_code == 200


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_rejected(environment, sample_food, name):
    client, _ = environment
    response = client.post("/food-library/", json={**sample_food, "name": name})
    assert response.status_code == 422, response.text
    assert client.get("/food-library/").json() == []


def test_missing_food_returns_404(environment, sample_food):
    client, _ = environment
    assert client.get("/food-library/99999").status_code == 404
    assert client.put("/food-library/99999", json=sample_food).status_code == 404
    assert client.delete("/food-library/99999").status_code == 404