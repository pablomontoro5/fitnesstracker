import pytest
from fastapi.testclient import TestClient

from app.db import get_connection
from app.main import app


@pytest.fixture(autouse=True)
def clear_nutrition_days():
    with get_connection() as connection:
        connection.execute("DELETE FROM nutrition_days")


def create_nutrition_day(
    client: TestClient,
    *,
    date: str = "2026-08-31",
) -> dict:
    response = client.post(
        "/nutrition-days/",
        json={
            "date": date,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_nutrition_meal(
    client: TestClient,
    *,
    day_id: int,
    name: str = "Desayuno",
    position: int = 1,
) -> dict:
    response = client.post(
        f"/nutrition-days/{day_id}/meals/",
        json={
            "name": name,
            "position": position,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_nutrition_food(
    client: TestClient,
    *,
    meal_id: int,
    name: str = "Avena",
    quantity_g: float = 80,
    calories: float = 304,
    protein_g: float = 10.4,
    carbs_g: float = 48.8,
    fat_g: float = 5.6,
    position: int = 1,
    notes: str | None = None,
) -> dict:
    response = client.post(
        f"/nutrition-meals/{meal_id}/foods/",
        json={
            "name": name,
            "quantity_g": quantity_g,
            "calories": calories,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "position": position,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_nutrition_food():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        response = client.post(
            f"/nutrition-meals/{meal['id']}/foods/",
            json={
                "name": "Avena",
                "quantity_g": 80,
                "calories": 304,
                "protein_g": 10.4,
                "carbs_g": 48.8,
                "fat_g": 5.6,
                "position": 1,
                "notes": "Pesada en seco.",
            },
        )

    assert response.status_code == 201

    food = response.json()

    assert food["nutrition_meal_id"] == meal["id"]
    assert food["name"] == "Avena"
    assert food["quantity_g"] == 80
    assert food["calories"] == 304
    assert food["protein_g"] == 10.4
    assert food["carbs_g"] == 48.8
    assert food["fat_g"] == 5.6
    assert food["position"] == 1
    assert food["notes"] == "Pesada en seco."


def test_list_nutrition_foods_orders_by_position():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        second_food = create_nutrition_food(
            client,
            meal_id=meal["id"],
            name="Leche",
            position=2,
        )
        first_food = create_nutrition_food(
            client,
            meal_id=meal["id"],
            name="Avena",
            position=1,
        )

        response = client.get(
            f"/nutrition-meals/{meal['id']}/foods/",
        )

    assert response.status_code == 200

    foods = response.json()

    assert [food["id"] for food in foods] == [
        first_food["id"],
        second_food["id"],
    ]


def test_nutrition_food_requires_existing_meal():
    with TestClient(app) as client:
        response = client.post(
            "/nutrition-meals/999999/foods/",
            json={
                "name": "Avena",
                "quantity_g": 80,
                "calories": 304,
                "protein_g": 10.4,
                "carbs_g": 48.8,
                "fat_g": 5.6,
                "position": 1,
                "notes": None,
            },
        )

    assert response.status_code == 404


def test_duplicate_nutrition_food_position_returns_conflict():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        create_nutrition_food(
            client,
            meal_id=meal["id"],
            position=1,
        )

        response = client.post(
            f"/nutrition-meals/{meal['id']}/foods/",
            json={
                "name": "Plátano",
                "quantity_g": 120,
                "calories": 107,
                "protein_g": 1.3,
                "carbs_g": 27,
                "fat_g": 0.4,
                "position": 1,
                "notes": None,
            },
        )

    assert response.status_code == 409


def test_get_nutrition_food():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )
        created_food = create_nutrition_food(
            client,
            meal_id=meal["id"],
        )

        response = client.get(
            f"/nutrition-foods/{created_food['id']}",
        )

    assert response.status_code == 200
    assert response.json() == created_food


def test_update_nutrition_food():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )
        created_food = create_nutrition_food(
            client,
            meal_id=meal["id"],
        )

        response = client.put(
            f"/nutrition-foods/{created_food['id']}",
            json={
                "name": "Arroz cocido",
                "quantity_g": 250,
                "calories": 325,
                "protein_g": 6,
                "carbs_g": 70,
                "fat_g": 0.8,
                "position": 2,
                "notes": "Pesado cocido.",
            },
        )

    assert response.status_code == 200

    food = response.json()

    assert food["id"] == created_food["id"]
    assert food["name"] == "Arroz cocido"
    assert food["quantity_g"] == 250
    assert food["calories"] == 325
    assert food["protein_g"] == 6
    assert food["carbs_g"] == 70
    assert food["fat_g"] == 0.8
    assert food["position"] == 2
    assert food["notes"] == "Pesado cocido."


def test_delete_nutrition_food():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )
        created_food = create_nutrition_food(
            client,
            meal_id=meal["id"],
        )

        delete_response = client.delete(
            f"/nutrition-foods/{created_food['id']}",
        )
        get_response = client.get(
            f"/nutrition-foods/{created_food['id']}",
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_negative_macros_are_rejected():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        response = client.post(
            f"/nutrition-meals/{meal['id']}/foods/",
            json={
                "name": "Avena",
                "quantity_g": 80,
                "calories": -1,
                "protein_g": 10.4,
                "carbs_g": 48.8,
                "fat_g": 5.6,
                "position": 1,
                "notes": None,
            },
        )

    assert response.status_code == 422