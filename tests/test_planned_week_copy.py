from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_and_login


client = TestClient(app)

# Lunes 5 y lunes 12 de octubre de 2026.
THIS_WEEK = "2026-10-05"
NEXT_WEEK = "2026-10-12"


def plan(headers, day, name="Pierna", template_id=None, notes=None):
    response = client.post(
        "/planned-workouts/",
        headers=headers,
        json={
            "scheduled_date": day,
            "workout_template_id": template_id,
            "name": name,
            "notes": notes,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def copy_week(headers, source=THIS_WEEK, target=NEXT_WEEK):
    return client.post(
        "/planned-workouts/copy-week",
        headers=headers,
        json={"source_start": source, "target_start": target},
    )


def planned(headers, start, end):
    return client.get(
        f"/planned-workouts/?start_date={start}&end_date={end}",
        headers=headers,
    ).json()


def test_requires_authentication():
    response = client.post(
        "/planned-workouts/copy-week",
        json={"source_start": THIS_WEEK, "target_start": NEXT_WEEK},
    )

    assert response.status_code == 401


def test_copies_the_week_keeping_weekday_name_and_notes():
    headers = register_and_login(client)
    plan(headers, "2026-10-05", "Pierna", notes="Pesado")   # lunes
    plan(headers, "2026-10-07", "Empuje")                    # miércoles
    plan(headers, "2026-10-11", "Tirón")                     # domingo

    response = copy_week(headers)

    assert response.status_code == 200
    assert response.json() == {"copied": 3, "skipped": 0}

    copied = planned(headers, "2026-10-12", "2026-10-18")

    assert [(p["scheduled_date"], p["name"]) for p in copied] == [
        ("2026-10-12", "Pierna"),
        ("2026-10-14", "Empuje"),
        ("2026-10-18", "Tirón"),
    ]
    assert copied[0]["notes"] == "Pesado"
    # La semana de origen no cambia.
    assert len(planned(headers, "2026-10-05", "2026-10-11")) == 3


def test_copies_become_planned_even_if_the_source_was_completed_or_skipped():
    headers = register_and_login(client)
    done = plan(headers, "2026-10-05", "Pierna")
    skipped = plan(headers, "2026-10-06", "Empuje")

    client.post(
        f"/planned-workouts/{done['id']}/complete",
        headers=headers,
        json={"completed_date": None},
    )
    client.put(
        f"/planned-workouts/{skipped['id']}",
        headers=headers,
        json={
            "scheduled_date": "2026-10-06", "workout_template_id": None,
            "name": "Empuje", "notes": None, "status": "skipped",
        },
    )

    assert copy_week(headers).json()["copied"] == 2

    copied = planned(headers, "2026-10-12", "2026-10-18")

    assert [p["status"] for p in copied] == ["planned", "planned"]
    assert [p["workout_session_id"] for p in copied] == [None, None]


def test_repeating_the_copy_does_not_duplicate():
    headers = register_and_login(client)
    plan(headers, "2026-10-05", "Pierna")
    plan(headers, "2026-10-07", "Empuje")

    copy_week(headers)
    second = copy_week(headers)

    assert second.json() == {"copied": 0, "skipped": 2}
    assert len(planned(headers, "2026-10-12", "2026-10-18")) == 2


def test_existing_sessions_in_the_target_are_kept_and_not_duplicated():
    headers = register_and_login(client)
    plan(headers, "2026-10-05", "Pierna")
    plan(headers, "2026-10-12", "Pierna")           # ya está en destino
    plan(headers, "2026-10-12", "Otra cosa")        # distinta, se conserva

    result = copy_week(headers).json()

    assert result == {"copied": 0, "skipped": 1}
    assert len(planned(headers, "2026-10-12", "2026-10-18")) == 2


def test_same_name_with_a_different_template_is_not_a_duplicate():
    headers = register_and_login(client)
    first = client.post(
        "/workout-templates/", headers=headers, json={"name": "A"},
    ).json()
    second = client.post(
        "/workout-templates/", headers=headers, json={"name": "B"},
    ).json()
    plan(headers, "2026-10-05", "Pierna", template_id=first["id"])
    plan(headers, "2026-10-12", "Pierna", template_id=second["id"])

    result = copy_week(headers).json()

    assert result == {"copied": 1, "skipped": 0}


def test_can_copy_backwards_and_to_a_distant_week():
    headers = register_and_login(client)
    plan(headers, "2026-10-12", "Pierna")

    assert copy_week(headers, source=NEXT_WEEK, target=THIS_WEEK).json()["copied"] == 1
    assert copy_week(headers, source=NEXT_WEEK, target="2026-11-02").json()["copied"] == 1
    assert [p["scheduled_date"] for p in planned(headers, "2026-11-02", "2026-11-08")] == [
        "2026-11-02",
    ]


def test_an_empty_week_copies_nothing():
    headers = register_and_login(client)

    assert copy_week(headers).json() == {"copied": 0, "skipped": 0}


def test_only_the_users_own_sessions_are_copied():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    plan(alice, "2026-10-05", "De Alice")

    assert copy_week(bob).json() == {"copied": 0, "skipped": 0}
    assert planned(bob, "2026-10-01", "2026-10-31") == []
    assert len(planned(alice, "2026-10-01", "2026-10-31")) == 1


def test_invalid_requests_are_rejected():
    headers = register_and_login(client)

    same = copy_week(headers, source=THIS_WEEK, target=THIS_WEEK)
    too_far = copy_week(headers, source=THIS_WEEK, target="2028-10-02")
    bad_date = client.post(
        "/planned-workouts/copy-week",
        headers=headers,
        json={"source_start": "nunca", "target_start": NEXT_WEEK},
    )

    assert same.status_code == 422
    assert too_far.status_code == 422
    assert bad_date.status_code == 422
