from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_nutrition_day(client: TestClient, *, headers: dict[str, str], date="2026-08-31") -> dict:
    response = client.post(
        "/nutrition-days/", headers=headers, json={"date": date, "notes": None}
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_nutrition_meal(
    client: TestClient,
    *,
    headers: dict[str, str],
    day_id: int,
    name: str = "Desayuno",
    position: int = 1,
) -> dict:
    response = client.post(
        f"/nutrition-days/{day_id}/meals/",
        headers=headers,
        json={"name": name, "position": position},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_nutrition_meal():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        meal = create_nutrition_meal(client, headers=headers, day_id=day["id"])
    assert meal["nutrition_day_id"] == day["id"]
    assert meal["name"] == "Desayuno"
    assert meal["position"] == 1


def test_list_nutrition_meals_orders_by_position():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        second = create_nutrition_meal(client, headers=headers, day_id=day["id"], name="Cena", position=2)
        first = create_nutrition_meal(client, headers=headers, day_id=day["id"])
        response = client.get(f"/nutrition-days/{day['id']}/meals/", headers=headers)
    assert response.status_code == 200
    assert response.json() == [first, second]


def test_nutrition_meal_requires_existing_day():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.post(
            "/nutrition-days/999999/meals/",
            headers=headers,
            json={"name": "Desayuno", "position": 1},
        )
    assert response.status_code == 404


def test_duplicate_nutrition_meal_position_returns_conflict():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        create_nutrition_meal(client, headers=headers, day_id=day["id"])
        response = client.post(
            f"/nutrition-days/{day['id']}/meals/",
            headers=headers,
            json={"name": "Almuerzo", "position": 1},
        )
    assert response.status_code == 409


def test_get_nutrition_meal():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        meal = create_nutrition_meal(client, headers=headers, day_id=day["id"])
        response = client.get(f"/nutrition-meals/{meal['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == meal


def test_update_nutrition_meal():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        meal = create_nutrition_meal(client, headers=headers, day_id=day["id"])
        response = client.put(
            f"/nutrition-meals/{meal['id']}",
            headers=headers,
            json={"name": "Almuerzo", "position": 2},
        )
    assert response.status_code == 200
    assert response.json() == {**meal, "name": "Almuerzo", "position": 2}


def test_delete_nutrition_meal():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        meal = create_nutrition_meal(client, headers=headers, day_id=day["id"])
        deleted = client.delete(f"/nutrition-meals/{meal['id']}", headers=headers)
        missing = client.get(f"/nutrition-meals/{meal['id']}", headers=headers)
    assert deleted.status_code == 204
    assert missing.status_code == 404


def test_other_users_meal_is_inaccessible():
    with TestClient(app) as client:
        ana = register_and_login(client, email="ana-meals@example.com", display_name="Ana")
        bruno = register_and_login(client, email="bruno-meals@example.com", display_name="Bruno")
        day = create_nutrition_day(client, headers=ana)
        meal = create_nutrition_meal(client, headers=ana, day_id=day["id"])
        list_response = client.get(f"/nutrition-days/{day['id']}/meals/", headers=bruno)
        create_response = client.post(
            f"/nutrition-days/{day['id']}/meals/",
            headers=bruno,
            json={"name": "Ajena", "position": 2},
        )
        get_response = client.get(f"/nutrition-meals/{meal['id']}", headers=bruno)
        update_response = client.put(
            f"/nutrition-meals/{meal['id']}",
            headers=bruno,
            json={"name": "Ajena", "position": 2},
        )
        delete_response = client.delete(f"/nutrition-meals/{meal['id']}", headers=bruno)
        owner_response = client.get(f"/nutrition-meals/{meal['id']}", headers=ana)
    assert [r.status_code for r in (
        list_response, create_response, get_response, update_response, delete_response
    )] == [404] * 5
    assert owner_response.json() == meal


def test_nutrition_meals_require_authentication():
    with TestClient(app) as client:
        response = client.get("/nutrition-meals/999999")
    assert response.status_code == 401