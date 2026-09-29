from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_day(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/nutrition-days/", headers=headers,
        json={"date": "2026-08-31", "notes": None},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_meal(client: TestClient, headers: dict[str, str], day_id: int) -> dict:
    response = client.post(
        f"/nutrition-days/{day_id}/meals/", headers=headers,
        json={"name": "Desayuno", "position": 1},
    )
    assert response.status_code == 201, response.text
    return response.json()


def food_payload(
    *, name="Avena", position=1, quantity_g=80, calories=304,
    protein_g=10.4, carbs_g=48.8, fat_g=5.6, notes=None,
) -> dict:
    return dict(
        name=name, position=position, quantity_g=quantity_g,
        calories=calories, protein_g=protein_g, carbs_g=carbs_g,
        fat_g=fat_g, notes=notes,
    )


def create_food(
    client: TestClient,
    headers: dict[str, str],
    meal_id: int,
    **overrides,
) -> dict:
    response = client.post(
        f"/nutrition-meals/{meal_id}/foods/", headers=headers,
        json=food_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_nutrition_food():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        food = create_food(client, headers, meal["id"], notes="Pesada en seco.")
    assert food == {
        "id": food["id"], "nutrition_meal_id": meal["id"],
        **food_payload(notes="Pesada en seco."),
    }


def test_list_nutrition_foods_orders_by_position():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        second = create_food(client, headers, meal["id"], name="Leche", position=2)
        first = create_food(client, headers, meal["id"])
        response = client.get(f"/nutrition-meals/{meal['id']}/foods/", headers=headers)
    assert response.status_code == 200
    assert response.json() == [first, second]


def test_nutrition_food_requires_existing_meal():
    with TestClient(app) as client:
        headers = register_and_login(client)
        response = client.post(
            "/nutrition-meals/999999/foods/", headers=headers,
            json=food_payload(),
        )
    assert response.status_code == 404


def test_duplicate_nutrition_food_position_returns_conflict():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        create_food(client, headers, meal["id"])
        response = client.post(
            f"/nutrition-meals/{meal['id']}/foods/", headers=headers,
            json=food_payload(name="Plátano", quantity_g=120, calories=107,
                              protein_g=1.3, carbs_g=27, fat_g=0.4),
        )
    assert response.status_code == 409


def test_get_nutrition_food():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        food = create_food(client, headers, meal["id"])
        response = client.get(f"/nutrition-foods/{food['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == food


def test_update_nutrition_food():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        food = create_food(client, headers, meal["id"])
        update = food_payload(
            name="Arroz cocido", quantity_g=250, calories=325,
            protein_g=6, carbs_g=70, fat_g=0.8, position=2,
            notes="Pesado cocido.",
        )
        response = client.put(
            f"/nutrition-foods/{food['id']}", headers=headers, json=update
        )
    assert response.status_code == 200
    assert response.json() == {**food, **update}


def test_delete_nutrition_food():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        food = create_food(client, headers, meal["id"])
        deleted = client.delete(f"/nutrition-foods/{food['id']}", headers=headers)
        missing = client.get(f"/nutrition-foods/{food['id']}", headers=headers)
    assert deleted.status_code == 204
    assert missing.status_code == 404


def test_negative_macros_are_rejected():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_day(client, headers)
        meal = create_meal(client, headers, day["id"])
        response = client.post(
            f"/nutrition-meals/{meal['id']}/foods/", headers=headers,
            json=food_payload(calories=-1),
        )
    assert response.status_code == 422


def test_other_users_food_is_inaccessible():
    with TestClient(app) as client:
        ana = register_and_login(client, email="ana-foods@example.com", display_name="Ana")
        bruno = register_and_login(client, email="bruno-foods@example.com", display_name="Bruno")
        day = create_day(client, ana)
        meal = create_meal(client, ana, day["id"])
        food = create_food(client, ana, meal["id"])
        listed = client.get(f"/nutrition-meals/{meal['id']}/foods/", headers=bruno)
        created = client.post(
            f"/nutrition-meals/{meal['id']}/foods/", headers=bruno,
            json=food_payload(position=2),
        )
        fetched = client.get(f"/nutrition-foods/{food['id']}", headers=bruno)
        updated = client.put(
            f"/nutrition-foods/{food['id']}", headers=bruno,
            json=food_payload(name="Ajeno"),
        )
        deleted = client.delete(f"/nutrition-foods/{food['id']}", headers=bruno)
        owner = client.get(f"/nutrition-foods/{food['id']}", headers=ana)
    assert [r.status_code for r in (listed, created, fetched, updated, deleted)] == [404] * 5
    assert owner.json() == food


def test_nutrition_foods_require_authentication():
    with TestClient(app) as client:
        response = client.get("/nutrition-foods/999999")
    assert response.status_code == 401