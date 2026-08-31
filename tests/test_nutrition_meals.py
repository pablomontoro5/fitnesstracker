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


def test_create_nutrition_meal():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)

        response = client.post(
            f"/nutrition-days/{nutrition_day['id']}/meals/",
            json={
                "name": "Desayuno",
                "position": 1,
            },
        )

    assert response.status_code == 201

    meal = response.json()

    assert meal["nutrition_day_id"] == nutrition_day["id"]
    assert meal["name"] == "Desayuno"
    assert meal["position"] == 1


def test_list_nutrition_meals_orders_by_position():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)

        second_meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
            name="Cena",
            position=2,
        )
        first_meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
            name="Desayuno",
            position=1,
        )

        response = client.get(
            f"/nutrition-days/{nutrition_day['id']}/meals/",
        )

    assert response.status_code == 200

    meals = response.json()

    assert [meal["id"] for meal in meals] == [
        first_meal["id"],
        second_meal["id"],
    ]


def test_nutrition_meal_requires_existing_day():
    with TestClient(app) as client:
        response = client.post(
            "/nutrition-days/999999/meals/",
            json={
                "name": "Desayuno",
                "position": 1,
            },
        )

    assert response.status_code == 404


def test_duplicate_nutrition_meal_position_returns_conflict():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)

        create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
            position=1,
        )

        response = client.post(
            f"/nutrition-days/{nutrition_day['id']}/meals/",
            json={
                "name": "Almuerzo",
                "position": 1,
            },
        )

    assert response.status_code == 409


def test_get_nutrition_meal():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        created_meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        response = client.get(
            f"/nutrition-meals/{created_meal['id']}",
        )

    assert response.status_code == 200
    assert response.json() == created_meal


def test_update_nutrition_meal():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        created_meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        response = client.put(
            f"/nutrition-meals/{created_meal['id']}",
            json={
                "name": "Almuerzo",
                "position": 2,
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == created_meal["id"]
    assert response.json()["name"] == "Almuerzo"
    assert response.json()["position"] == 2


def test_delete_nutrition_meal():
    with TestClient(app) as client:
        nutrition_day = create_nutrition_day(client)
        created_meal = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
        )

        delete_response = client.delete(
            f"/nutrition-meals/{created_meal['id']}",
        )
        get_response = client.get(
            f"/nutrition-meals/{created_meal['id']}",
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404