import pytest

from app.db import get_connection
from fastapi.testclient import TestClient


from app.main import app

@pytest.fixture(autouse=True)
def clear_nutrition_days():
    with get_connection() as connection:
        connection.execute("DELETE FROM nutrition_days")


def create_nutrition_day(
    client: TestClient,
    *,
    date: str = "2026-08-31",
    notes: str | None = "Día de prueba.",
) -> dict:
    response = client.post(
        "/nutrition-days/",
        json={
            "date": date,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_nutrition_day():
    with TestClient(app) as client:
        response = client.post(
            "/nutrition-days/",
            json={
                "date": "2026-08-31",
                "notes": "Comida preparada en casa.",
            },
        )

    assert response.status_code == 201

    nutrition_day = response.json()

    assert nutrition_day["date"] == "2026-08-31"
    assert nutrition_day["notes"] == "Comida preparada en casa."


def test_list_nutrition_days_orders_by_date_descending():
    with TestClient(app) as client:
        older_day = create_nutrition_day(
            client,
            date="2026-08-29",
        )
        newer_day = create_nutrition_day(
            client,
            date="2026-08-30",
        )

        response = client.get("/nutrition-days/")

    assert response.status_code == 200

    nutrition_days = response.json()
    nutrition_day_ids = [nutrition_day["id"] for nutrition_day in nutrition_days]

    assert newer_day["id"] in nutrition_day_ids
    assert older_day["id"] in nutrition_day_ids
    assert (
        nutrition_day_ids.index(newer_day["id"])
        < nutrition_day_ids.index(older_day["id"])
    )


def test_get_nutrition_day():
    with TestClient(app) as client:
        created_day = create_nutrition_day(client)

        response = client.get(f"/nutrition-days/{created_day['date']}")

    assert response.status_code == 200
    assert response.json() == created_day


def test_update_nutrition_day():
    with TestClient(app) as client:
        created_day = create_nutrition_day(client)

        response = client.put(
            f"/nutrition-days/{created_day['date']}",
            json={
                "notes": "Cena especial.",
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == created_day["id"]
    assert response.json()["date"] == "2026-08-31"
    assert response.json()["notes"] == "Cena especial."


def test_delete_nutrition_day():
    with TestClient(app) as client:
        created_day = create_nutrition_day(client)

        delete_response = client.delete(
            f"/nutrition-days/{created_day['date']}",
        )
        get_response = client.get(
            f"/nutrition-days/{created_day['date']}",
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_duplicate_nutrition_day_date_returns_conflict():
    with TestClient(app) as client:
        create_nutrition_day(client)

        response = client.post(
            "/nutrition-days/",
            json={
                "date": "2026-08-31",
                "notes": "Registro duplicado.",
            },
        )

    assert response.status_code == 409