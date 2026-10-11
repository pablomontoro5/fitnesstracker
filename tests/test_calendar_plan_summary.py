from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


client = TestClient(app)

TODAY = "2026-10-10"
START, END = "2026-10-05", "2026-10-11"   # lunes a domingo


def plan(headers, day, name="Pierna"):
    response = client.post(
        "/planned-workouts/",
        headers=headers,
        json={"scheduled_date": day, "name": name},
    )

    assert response.status_code == 201, response.text
    return response.json()


def complete(headers, planned):
    response = client.post(
        f"/planned-workouts/{planned['id']}/complete",
        headers=headers,
        json={"completed_date": None},
    )

    assert response.status_code == 201, response.text


def skip(headers, planned):
    response = client.put(
        f"/planned-workouts/{planned['id']}",
        headers=headers,
        json={
            "scheduled_date": planned["scheduled_date"],
            "workout_template_id": None,
            "name": planned["name"],
            "notes": None,
            "status": "skipped",
        },
    )

    assert response.status_code == 200, response.text


def activity(headers, start=START, end=END, today=TODAY):
    query = f"start_date={start}&end_date={end}"

    if today is not None:
        query += f"&today={today}"

    response = client.get(f"/calendar/activity?{query}", headers=headers)

    assert response.status_code == 200, response.text
    return response.json()


def day_of(result, value):
    return next(day for day in result["days"] if day["date"] == value)


def test_summary_is_empty_without_plans():
    headers = register_and_login(client)

    summary = activity(headers)["plan_summary"]

    assert summary == {
        "total": 0, "completed": 0, "skipped": 0,
        "overdue": 0, "upcoming": 0, "completion_rate": None,
    }


def test_summary_counts_each_state():
    headers = register_and_login(client)
    done = plan(headers, "2026-10-05", "Hecha")
    skipped = plan(headers, "2026-10-06", "Omitida")
    plan(headers, "2026-10-07", "Vencida")       # pasada y sin hacer
    plan(headers, "2026-10-12", "Futura")        # fuera del periodo
    plan(headers, "2026-10-11", "Por hacer")     # futura dentro del periodo
    complete(headers, done)
    skip(headers, skipped)

    summary = activity(headers)["plan_summary"]

    assert summary["total"] == 4
    assert summary["completed"] == 1
    assert summary["skipped"] == 1
    assert summary["overdue"] == 1
    assert summary["upcoming"] == 1
    # Solo cuenta lo que ya tocaba: 1 hecha de 3 (hecha + omitida + vencida).
    assert summary["completion_rate"] == 33.3


def test_a_plan_for_today_is_upcoming_not_overdue():
    headers = register_and_login(client)
    plan(headers, TODAY, "De hoy")

    result = activity(headers)

    assert result["plan_summary"]["overdue"] == 0
    assert result["plan_summary"]["upcoming"] == 1
    assert result["plan_summary"]["completion_rate"] is None
    assert day_of(result, TODAY)["planned_workouts"][0]["is_overdue"] is False


def test_overdue_flag_is_set_only_on_past_planned_sessions():
    headers = register_and_login(client)
    past = plan(headers, "2026-10-06", "Pasada")
    done = plan(headers, "2026-10-07", "Completada")
    plan(headers, "2026-10-11", "Futura")
    complete(headers, done)

    result = activity(headers)

    assert day_of(result, "2026-10-06")["planned_workouts"][0] == {
        "id": past["id"], "name": "Pasada", "status": "planned",
        "is_overdue": True, "kind": "workout", "target_distance_km": None,
    }
    assert day_of(result, "2026-10-07")["planned_workouts"][0]["is_overdue"] is False
    assert day_of(result, "2026-10-11")["planned_workouts"][0]["is_overdue"] is False


def test_the_today_parameter_decides_what_is_overdue():
    headers = register_and_login(client)
    plan(headers, "2026-10-08", "Jueves")

    assert activity(headers, today="2026-10-08")["plan_summary"]["overdue"] == 0
    assert activity(headers, today="2026-10-09")["plan_summary"]["overdue"] == 1


def test_today_defaults_to_the_server_date():
    headers = register_and_login(client)
    plan(headers, "2020-01-01", "Muy antigua")

    result = activity(headers, start="2020-01-01", end="2020-01-07", today=None)

    assert result["plan_summary"]["overdue"] == 1


def test_only_plans_inside_the_period_count():
    headers = register_and_login(client)
    plan(headers, "2026-10-05", "Dentro")
    plan(headers, "2026-09-28", "Antes")
    plan(headers, "2026-10-19", "Después")

    assert activity(headers)["plan_summary"]["total"] == 1


def test_only_the_users_own_plans_count():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    plan(alice, "2026-10-06", "De Alice")

    assert activity(bob)["plan_summary"]["total"] == 0
    assert activity(alice)["plan_summary"]["total"] == 1


def test_completed_overdue_plan_no_longer_counts_as_overdue():
    headers = register_and_login(client)
    late = plan(headers, "2026-10-06", "Tarde")

    assert activity(headers)["plan_summary"]["overdue"] == 1

    complete(headers, late)
    summary = activity(headers)["plan_summary"]

    assert summary["overdue"] == 0
    assert summary["completed"] == 1
    assert summary["completion_rate"] == 100.0
