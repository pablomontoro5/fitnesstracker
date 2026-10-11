import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.db import get_connection
from app.main import app
from tests.conftest import register_and_login


client = TestClient(app)
PASSWORD = "password-segura-123"


def create_food(headers, name, calories, protein, carbs, fat):
    response = client.post(
        "/food-library/",
        json={
            "name": name, "calories_per_100g": calories,
            "protein_per_100g": protein, "carbs_per_100g": carbs,
            "fat_per_100g": fat,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_template(headers, name="Desayuno", items=(("Avena", 370, 13, 60, 7, 50),)):
    """Plantilla con elementos: (nombre, kcal, prot, carb, grasa por 100 g, gramos)."""
    template = client.post(
        "/meal-templates/", json={"name": name}, headers=headers,
    ).json()

    for food_name, calories, protein, carbs, fat, grams in items:
        food_id = create_food(headers, food_name, calories, protein, carbs, fat)
        added = client.post(
            f"/meal-templates/{template['id']}/items",
            json={"food_id": food_id, "grams": grams},
            headers=headers,
        )

        assert added.status_code == 201, added.text

    return template


def plan(headers, day="2026-10-12", template_id=None, name=None, notes=None):
    return client.post(
        "/planned-meals/",
        headers=headers,
        json={
            "scheduled_date": day, "meal_template_id": template_id,
            "name": name, "notes": notes,
        },
    )


def complete(headers, planned_id, **body):
    return client.post(
        f"/planned-meals/{planned_id}/complete",
        headers=headers,
        json={"completed_date": None, **body},
    )


def foods_of_meal(meal_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT name, quantity_g, calories, protein_g, carbs_g, fat_g, "
            "position FROM nutrition_foods WHERE nutrition_meal_id = ? "
            "ORDER BY position",
            (meal_id,),
        ).fetchall()


def planned(headers, start="2026-10-01", end="2026-10-31"):
    return client.get(
        f"/planned-meals/?start_date={start}&end_date={end}", headers=headers,
    ).json()


def test_requires_authentication():
    assert client.get("/planned-meals/").status_code == 401
    assert client.post("/planned-meals/", json={}).status_code == 401


def test_plan_a_meal_from_a_template_takes_its_name_and_totals():
    headers = register_and_login(client)
    template = create_template(headers, "Desayuno")

    response = plan(headers, template_id=template["id"])

    assert response.status_code == 201, response.text
    meal = response.json()
    assert meal["name"] == "Desayuno"
    assert meal["status"] == "planned"
    assert meal["nutrition_meal_id"] is None
    # 50 g de avena: 185 kcal, 6,5 g de proteína, 30 g de carbohidratos, 3,5 de grasa.
    assert (meal["calories"], meal["protein_g"], meal["carbs_g"], meal["fat_g"]) == (
        185.0, 6.5, 30.0, 3.5,
    )


def test_a_name_can_replace_the_template_name_or_be_used_alone():
    headers = register_and_login(client)
    template = create_template(headers)

    renamed = plan(headers, template_id=template["id"], name="Merienda").json()
    free = plan(headers, name="Cena fuera").json()

    assert renamed["name"] == "Merienda"
    assert free["name"] == "Cena fuera"
    assert free["meal_template_id"] is None
    assert free["calories"] is None


def test_validation_and_ownership():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    template = create_template(alice)

    assert plan(alice).status_code == 422                      # ni plantilla ni nombre
    assert plan(alice, name="   ").status_code == 422
    assert plan(alice, template_id=99999).status_code == 404
    assert plan(bob, template_id=template["id"]).status_code == 404
    assert client.post(
        "/planned-meals/", headers=alice,
        json={"scheduled_date": "nunca", "name": "X"},
    ).status_code == 422


def test_list_filters_by_range_and_is_private():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    plan(alice, day="2026-10-05", name="Lunes")
    plan(alice, day="2026-10-20", name="Fuera")
    plan(bob, day="2026-10-05", name="De Bob")

    inside = planned(alice, "2026-10-05", "2026-10-11")

    assert [m["name"] for m in inside] == ["Lunes"]
    assert [m["name"] for m in planned(bob)] == ["De Bob"]
    assert client.get(
        "/planned-meals/?start_date=2026-10-10&end_date=2026-10-01", headers=alice,
    ).status_code == 422


def test_update_and_delete_and_completed_ones_are_locked():
    headers = register_and_login(client)
    first = plan(headers, name="Cena").json()
    done = plan(headers, name="Hecha").json()
    complete(headers, done["id"])

    updated = client.put(
        f"/planned-meals/{first['id']}", headers=headers,
        json={
            "scheduled_date": "2026-10-13", "meal_template_id": None,
            "name": "Cena ligera", "notes": "Sin sal", "status": "skipped",
        },
    )
    locked_update = client.put(
        f"/planned-meals/{done['id']}", headers=headers,
        json={
            "scheduled_date": "2026-10-13", "meal_template_id": None,
            "name": "X", "notes": None, "status": "planned",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Cena ligera"
    assert updated.json()["status"] == "skipped"
    assert locked_update.status_code == 409
    assert client.delete(f"/planned-meals/{done['id']}", headers=headers).status_code == 409
    assert client.delete(f"/planned-meals/{first['id']}", headers=headers).status_code == 204
    assert client.get(f"/planned-meals/{first['id']}", headers=headers).status_code == 404


def test_completing_registers_the_meal_and_its_foods_in_the_nutrition_diary():
    headers = register_and_login(client)
    template = create_template(
        headers, "Desayuno",
        items=(("Avena", 370, 13, 60, 7, 50), ("Leche", 46, 3.4, 4.8, 1.6, 200)),
    )
    meal = plan(headers, day="2026-10-12", template_id=template["id"]).json()

    response = complete(headers, meal["id"])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["foods_added"] == 2
    assert body["planned_meal"]["status"] == "completed"
    assert body["planned_meal"]["nutrition_meal_id"] == body["nutrition_meal_id"]

    with get_connection() as connection:
        day = connection.execute(
            "SELECT date FROM nutrition_days WHERE id = ?",
            (body["nutrition_day_id"],),
        ).fetchone()
        nutrition_meal = connection.execute(
            "SELECT name, position FROM nutrition_meals WHERE id = ?",
            (body["nutrition_meal_id"],),
        ).fetchone()

    assert day["date"] == "2026-10-12"
    assert (nutrition_meal["name"], nutrition_meal["position"]) == ("Desayuno", 1)

    foods = foods_of_meal(body["nutrition_meal_id"])

    assert [f["name"] for f in foods] == ["Avena", "Leche"]
    assert [f["position"] for f in foods] == [1, 2]
    # Macros calculadas para la cantidad: 50 g de avena y 200 g de leche.
    assert (foods[0]["quantity_g"], foods[0]["calories"], foods[0]["protein_g"]) == (50, 185, 6.5)
    assert (foods[1]["quantity_g"], foods[1]["calories"], foods[1]["fat_g"]) == (200, 92, 3.2)


def test_completing_reuses_the_day_and_appends_meals_in_order():
    headers = register_and_login(client)
    template = create_template(headers)
    first = plan(headers, day="2026-10-12", template_id=template["id"], name="Desayuno").json()
    second = plan(headers, day="2026-10-12", template_id=template["id"], name="Merienda").json()

    one = complete(headers, first["id"]).json()
    two = complete(headers, second["id"]).json()

    assert one["nutrition_day_id"] == two["nutrition_day_id"]

    with get_connection() as connection:
        positions = connection.execute(
            "SELECT name, position FROM nutrition_meals "
            "WHERE nutrition_day_id = ? ORDER BY position",
            (one["nutrition_day_id"],),
        ).fetchall()
        days = connection.execute("SELECT COUNT(*) AS n FROM nutrition_days").fetchone()["n"]

    assert [(m["name"], m["position"]) for m in positions] == [
        ("Desayuno", 1), ("Merienda", 2),
    ]
    assert days == 1


def test_completing_after_a_manual_meal_goes_to_the_end_of_that_day():
    headers = register_and_login(client)
    day = client.post(
        "/nutrition-days/", headers=headers,
        json={"date": "2026-10-12", "notes": "Manual"},
    ).json()
    client.post(
        f"/nutrition-days/{day['id']}/meals/", headers=headers,
        json={"name": "Comida manual", "position": 1},
    )
    meal = plan(headers, day="2026-10-12", name="Cena").json()

    body = complete(headers, meal["id"]).json()

    assert body["nutrition_day_id"] == day["id"]

    with get_connection() as connection:
        position = connection.execute(
            "SELECT position FROM nutrition_meals WHERE id = ?",
            (body["nutrition_meal_id"],),
        ).fetchone()["position"]

    assert position == 2


def test_completing_can_use_another_day_and_works_without_a_template():
    headers = register_and_login(client)
    meal = plan(headers, day="2026-10-12", name="Cena fuera").json()

    body = complete(headers, meal["id"], completed_date="2026-10-13").json()

    assert body["foods_added"] == 0
    with get_connection() as connection:
        date = connection.execute(
            "SELECT date FROM nutrition_days WHERE id = ?", (body["nutrition_day_id"],),
        ).fetchone()["date"]

    assert date == "2026-10-13"


def test_a_meal_cannot_be_completed_twice_or_after_skipping_or_by_others():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    done = plan(alice, name="Hecha").json()
    skipped = plan(alice, name="Omitida").json()
    mine = plan(alice, name="Mía").json()
    client.put(
        f"/planned-meals/{skipped['id']}", headers=alice,
        json={
            "scheduled_date": "2026-10-12", "meal_template_id": None,
            "name": "Omitida", "notes": None, "status": "skipped",
        },
    )

    assert complete(alice, done["id"]).status_code == 201
    assert complete(alice, done["id"]).status_code == 409
    assert complete(alice, skipped["id"]).status_code == 409
    assert complete(bob, mine["id"]).status_code == 404

    with get_connection() as connection:
        meals = connection.execute("SELECT COUNT(*) AS n FROM nutrition_meals").fetchone()["n"]

    assert meals == 1


def test_deleting_the_template_keeps_the_plan_and_completes_it_empty():
    headers = register_and_login(client)
    template = create_template(headers)
    meal = plan(headers, template_id=template["id"]).json()

    client.delete(f"/meal-templates/{template['id']}", headers=headers)

    after = client.get(f"/planned-meals/{meal['id']}", headers=headers).json()
    body = complete(headers, meal["id"]).json()

    assert after["meal_template_id"] is None
    assert after["name"] == "Desayuno"
    assert after["calories"] is None
    assert body["foods_added"] == 0


def test_deleting_the_nutrition_meal_unlinks_the_planned_meal():
    headers = register_and_login(client)
    meal = plan(headers, name="Cena").json()
    body = complete(headers, meal["id"]).json()

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM nutrition_meals WHERE id = ?", (body["nutrition_meal_id"],),
        )

    after = client.get(f"/planned-meals/{meal['id']}", headers=headers).json()

    assert after["status"] == "completed"
    assert after["nutrition_meal_id"] is None


def copy_week(headers, source="2026-10-05", target="2026-10-12"):
    return client.post(
        "/planned-meals/copy-week", headers=headers,
        json={"source_start": source, "target_start": target},
    )


def test_copy_week_repeats_meals_without_duplicating_and_resets_status():
    headers = register_and_login(client)
    template = create_template(headers)
    plan(headers, day="2026-10-05", template_id=template["id"], name="Desayuno", notes="Rápido")
    done = plan(headers, day="2026-10-07", name="Cena").json()
    complete(headers, done["id"])

    first = copy_week(headers).json()
    second = copy_week(headers).json()
    copied = planned(headers, "2026-10-12", "2026-10-18")

    assert first == {"copied": 2, "skipped": 0}
    assert second == {"copied": 0, "skipped": 2}
    assert [(m["scheduled_date"], m["name"], m["status"]) for m in copied] == [
        ("2026-10-12", "Desayuno", "planned"),
        ("2026-10-14", "Cena", "planned"),
    ]
    assert copied[0]["notes"] == "Rápido"
    assert copied[0]["meal_template_id"] == template["id"]
    assert all(m["nutrition_meal_id"] is None for m in copied)


def test_copy_week_is_private_and_validates():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    plan(alice, day="2026-10-05", name="De Alice")

    assert copy_week(bob).json() == {"copied": 0, "skipped": 0}
    assert copy_week(alice, target="2026-10-05").status_code == 422
    assert copy_week(alice, target="2028-10-02").status_code == 422
    assert copy_week(alice).json() == {"copied": 1, "skipped": 0}


def upload(headers, data):
    return client.post(
        "/restores/account", headers=headers,
        files={"file": ("export.json", BytesIO(json.dumps(data).encode()), "application/json")},
        data={"password": PASSWORD},
    )


def test_export_and_restore_keep_planned_meals_and_relink_template_and_meal():
    headers = register_and_login(client)
    template = create_template(headers, "Desayuno")
    open_meal = plan(headers, day="2026-10-13", template_id=template["id"]).json()
    done = plan(headers, day="2026-10-12", template_id=template["id"], name="Hecha").json()
    complete(headers, done["id"])

    exported = client.get("/exports/fitness-tracker.json", headers=headers).json()
    by_name = {m["name"]: m for m in exported["planned_meals"]}

    assert exported["format_version"] == 4
    assert by_name["Hecha"]["status"] == "completed"
    assert by_name["Hecha"]["nutrition_meal_id"] is not None
    assert by_name["Desayuno"]["meal_template_id"] == exported["meal_templates"][0]["id"]

    with get_connection() as connection:
        connection.execute("DELETE FROM planned_meals")
        connection.execute("DELETE FROM nutrition_days")
        connection.execute("DELETE FROM meal_templates")

    assert upload(headers, exported).status_code == 200

    restored = {m["name"]: m for m in planned(headers)}
    new_template = client.get("/meal-templates/", headers=headers).json()[0]

    assert restored["Desayuno"]["meal_template_id"] == new_template["id"]
    assert restored["Desayuno"]["status"] == "planned"
    assert restored["Hecha"]["status"] == "completed"

    with get_connection() as connection:
        meal = connection.execute(
            "SELECT name FROM nutrition_meals WHERE id = ?",
            (restored["Hecha"]["nutrition_meal_id"],),
        ).fetchone()

    assert meal["name"] == "Hecha"
    assert open_meal["id"] != restored["Desayuno"]["id"]


def test_restoring_an_export_without_planned_meals_leaves_existing_ones_alone():
    headers = register_and_login(client)
    plan(headers, name="Se queda")

    old_export = {
        "exported_at": "2026-01-01T00:00:00", "format_version": 3,
        "daily_logs": [],
    }

    assert upload(headers, old_export).status_code == 200
    assert [m["name"] for m in planned(headers)] == ["Se queda"]
