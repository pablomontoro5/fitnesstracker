from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


def create_nutrition_day(
    client: TestClient,
    *,
    headers: dict[str, str],
    date: str = "2026-08-31",
    notes: str | None = "Día de prueba.",
) -> dict:
    response = client.post(
        "/nutrition-days/",
        headers=headers,
        json={"date": date, "notes": notes},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_nutrition_day():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(
            client,
            headers=headers,
            notes="Comida preparada en casa.",
        )
    assert day["date"] == "2026-08-31"
    assert day["notes"] == "Comida preparada en casa."


def test_list_nutrition_days_orders_by_date_descending():
    with TestClient(app) as client:
        headers = register_and_login(client)
        older = create_nutrition_day(client, headers=headers, date="2026-08-29")
        newer = create_nutrition_day(client, headers=headers, date="2026-08-30")
        response = client.get("/nutrition-days/", headers=headers)
    assert response.status_code == 200
    assert response.json() == [newer, older]


def test_get_nutrition_day():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        response = client.get(f"/nutrition-days/{day['date']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == day


def test_update_nutrition_day():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        response = client.put(
            f"/nutrition-days/{day['date']}",
            headers=headers,
            json={"notes": "Cena especial."},
        )
    assert response.status_code == 200
    assert response.json() == {**day, "notes": "Cena especial."}


def test_delete_nutrition_day():
    with TestClient(app) as client:
        headers = register_and_login(client)
        day = create_nutrition_day(client, headers=headers)
        deleted = client.delete(f"/nutrition-days/{day['date']}", headers=headers)
        missing = client.get(f"/nutrition-days/{day['date']}", headers=headers)
    assert deleted.status_code == 204
    assert missing.status_code == 404


def test_duplicate_nutrition_day_date_returns_conflict():
    with TestClient(app) as client:
        headers = register_and_login(client)
        create_nutrition_day(client, headers=headers)
        response = client.post(
            "/nutrition-days/",
            headers=headers,
            json={"date": "2026-08-31", "notes": "Duplicado."},
        )
    assert response.status_code == 409


def test_two_users_can_use_same_date_without_sharing_days():
    with TestClient(app) as client:
        ana = register_and_login(
            client, email="ana-days@example.com", display_name="Ana"
        )
        bruno = register_and_login(
            client, email="bruno-days@example.com", display_name="Bruno"
        )
        ana_day = create_nutrition_day(client, headers=ana, notes="De Ana")
        bruno_day = create_nutrition_day(client, headers=bruno, notes="De Bruno")
        ana_list = client.get("/nutrition-days/", headers=ana)
        bruno_list = client.get("/nutrition-days/", headers=bruno)
        ana_get = client.get("/nutrition-days/2026-08-31", headers=ana)
        bruno_get = client.get("/nutrition-days/2026-08-31", headers=bruno)
    assert ana_day["id"] != bruno_day["id"]
    assert ana_list.json() == [ana_day]
    assert bruno_list.json() == [bruno_day]
    assert ana_get.json() == ana_day
    assert bruno_get.json() == bruno_day


def test_other_users_exclusive_date_is_hidden():
    with TestClient(app) as client:
        ana = register_and_login(
            client, email="ana-exclusive@example.com", display_name="Ana"
        )
        bruno = register_and_login(
            client, email="bruno-exclusive@example.com", display_name="Bruno"
        )
        day = create_nutrition_day(client, headers=ana)
        path = f"/nutrition-days/{day['date']}"
        get_response = client.get(path, headers=bruno)
        put_response = client.put(path, headers=bruno, json={"notes": "Ajena"})
        delete_response = client.delete(path, headers=bruno)
        owner_response = client.get(path, headers=ana)
    assert [r.status_code for r in (get_response, put_response, delete_response)] == [404] * 3
    assert owner_response.json() == day


def test_nutrition_days_require_authentication():
    with TestClient(app) as client:
        response = client.get("/nutrition-days/")
    assert response.status_code == 401