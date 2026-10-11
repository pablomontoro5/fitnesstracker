import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.db import IntegrityError, get_connection
from app.main import app
from tests.conftest import register_and_login


client = TestClient(app)
PASSWORD = "password-segura-123"


def plan_run(headers, day="2026-10-06", distance=10.0, name=None, **extra):
    response = client.post(
        "/planned-workouts/",
        headers=headers,
        json={
            "scheduled_date": day,
            "kind": "run",
            "target_distance_km": distance,
            "name": name,
            **extra,
        },
    )

    return response


def complete(headers, planned_id, **body):
    return client.post(
        f"/planned-workouts/{planned_id}/complete",
        headers=headers,
        json={"completed_date": None, **body},
    )


def runs_of(headers):
    return client.get("/runs/", headers=headers).json()


def test_a_run_can_be_planned_with_a_target_distance_and_a_default_name():
    headers = register_and_login(client)

    response = plan_run(headers, distance=12.5)

    assert response.status_code == 201, response.text
    planned = response.json()
    assert planned["kind"] == "run"
    assert planned["target_distance_km"] == 12.5
    assert planned["name"] == "Carrera"
    assert planned["status"] == "planned"
    assert planned["run_id"] is None
    assert planned["workout_template_id"] is None


def test_a_run_can_have_its_own_name_and_no_distance():
    headers = register_and_login(client)

    planned = plan_run(headers, distance=None, name="Rodaje suave").json()

    assert planned["name"] == "Rodaje suave"
    assert planned["target_distance_km"] is None


def test_kind_specific_fields_are_validated():
    headers = register_and_login(client)
    template = client.post(
        "/workout-templates/", headers=headers, json={"name": "A"},
    ).json()

    run_with_template = plan_run(
        headers, workout_template_id=template["id"],
    )
    workout_with_distance = client.post(
        "/planned-workouts/",
        headers=headers,
        json={
            "scheduled_date": "2026-10-06", "name": "Pierna",
            "target_distance_km": 5,
        },
    )
    bad_distance = plan_run(headers, distance=0)
    unknown_kind = client.post(
        "/planned-workouts/",
        headers=headers,
        json={"scheduled_date": "2026-10-06", "name": "X", "kind": "swim"},
    )

    assert run_with_template.status_code == 422
    assert workout_with_distance.status_code == 422
    assert bad_distance.status_code == 422
    assert unknown_kind.status_code == 422


def test_the_database_itself_rejects_inconsistent_rows():
    headers = register_and_login(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with pytest.raises(IntegrityError):
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO planned_workouts (user_id, scheduled_date, kind, "
                "target_distance_km, name) VALUES (?, ?, 'workout', 5, 'X')",
                (user_id, "2026-10-06"),
            )


def test_a_planned_run_can_be_updated_and_skipped():
    headers = register_and_login(client)
    planned = plan_run(headers, distance=10).json()

    response = client.put(
        f"/planned-workouts/{planned['id']}",
        headers=headers,
        json={
            "scheduled_date": "2026-10-07", "target_distance_km": 15,
            "workout_template_id": None, "name": "Tirada larga",
            "notes": "Con calma", "status": "skipped",
        },
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["kind"] == "run"
    assert updated["target_distance_km"] == 15
    assert updated["status"] == "skipped"


def test_update_rejects_fields_that_do_not_fit_the_kind():
    headers = register_and_login(client)
    run = plan_run(headers).json()
    workout = client.post(
        "/planned-workouts/", headers=headers,
        json={"scheduled_date": "2026-10-06", "name": "Pierna"},
    ).json()
    template = client.post(
        "/workout-templates/", headers=headers, json={"name": "A"},
    ).json()

    def update(planned_id, **fields):
        body = {
            "scheduled_date": "2026-10-06", "workout_template_id": None,
            "name": "X", "notes": None, "status": "planned", **fields,
        }
        return client.put(
            f"/planned-workouts/{planned_id}", headers=headers, json=body,
        )

    assert update(run["id"], workout_template_id=template["id"]).status_code == 422
    assert update(workout["id"], target_distance_km=5).status_code == 422


def test_completing_a_run_creates_the_run_record_and_links_it():
    headers = register_and_login(client)
    planned = plan_run(headers, day="2026-10-06", distance=10).json()

    response = complete(headers, planned["id"], duration_seconds=3000)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["workout_session"] is None
    assert body["run"]["distance_km"] == 10          # la objetivo
    assert body["run"]["duration_seconds"] == 3000
    assert body["run"]["average_pace_seconds_km"] == 300
    assert body["run"]["date"] == "2026-10-06"       # la fecha planificada
    assert body["planned_workout"]["status"] == "completed"
    assert body["planned_workout"]["run_id"] == body["run"]["id"]

    assert [r["id"] for r in runs_of(headers)] == [body["run"]["id"]]
    # No crea ninguna sesión de gimnasio.
    assert client.get("/workout-sessions", headers=headers).json() == []


def test_completing_a_run_can_override_distance_and_date_and_keeps_notes():
    headers = register_and_login(client)
    planned = plan_run(
        headers, day="2026-10-06", distance=10, notes="Con cuestas",
    ).json()

    body = complete(
        headers, planned["id"], distance_km=8.4, duration_seconds=2520,
        completed_date="2026-10-07",
    ).json()

    assert body["run"]["distance_km"] == 8.4
    assert body["run"]["date"] == "2026-10-07"
    assert body["run"]["notes"] == "Con cuestas"


def test_completing_a_run_requires_duration_and_a_distance():
    headers = register_and_login(client)
    with_target = plan_run(headers, distance=10).json()
    without_target = plan_run(headers, distance=None, name="Libre").json()

    no_duration = complete(headers, with_target["id"])
    no_distance = complete(headers, without_target["id"], duration_seconds=1800)
    bad_duration = complete(headers, with_target["id"], duration_seconds=0)

    assert no_duration.status_code == 422
    assert no_distance.status_code == 422
    assert bad_duration.status_code == 422
    assert runs_of(headers) == []

    assert complete(
        headers, without_target["id"], distance_km=5, duration_seconds=1800,
    ).status_code == 201


def test_a_planned_run_cannot_be_completed_twice_or_after_skipping():
    headers = register_and_login(client)
    done = plan_run(headers).json()
    skipped = plan_run(headers, name="Omitida").json()
    client.put(
        f"/planned-workouts/{skipped['id']}", headers=headers,
        json={
            "scheduled_date": "2026-10-06", "workout_template_id": None,
            "name": "Omitida", "notes": None, "status": "skipped",
        },
    )

    assert complete(headers, done["id"], duration_seconds=3000).status_code == 201

    assert complete(headers, done["id"], duration_seconds=3000).status_code == 409
    assert complete(headers, skipped["id"], duration_seconds=3000).status_code == 409
    assert len(runs_of(headers)) == 1


def test_gym_sessions_still_complete_into_sessions_and_reject_run_fields():
    headers = register_and_login(client)
    workout = client.post(
        "/planned-workouts/", headers=headers,
        json={"scheduled_date": "2026-10-06", "name": "Pierna"},
    ).json()

    rejected = complete(headers, workout["id"], duration_seconds=3000)
    accepted = complete(headers, workout["id"])

    assert rejected.status_code == 422
    assert accepted.status_code == 201
    assert accepted.json()["workout_session"]["name"] == "Pierna"
    assert accepted.json()["run"] is None
    assert runs_of(headers) == []


def test_a_completed_planned_run_cannot_be_deleted_like_any_completed_plan():
    headers = register_and_login(client)
    planned = plan_run(headers).json()
    complete(headers, planned["id"], duration_seconds=3000)

    assert client.delete(
        f"/planned-workouts/{planned['id']}", headers=headers,
    ).status_code == 409
    assert len(runs_of(headers)) == 1


def test_deleting_the_run_record_unlinks_the_planned_run():
    headers = register_and_login(client)
    planned = plan_run(headers).json()
    run_id = complete(headers, planned["id"], duration_seconds=3000).json()["run"]["id"]

    assert client.delete(f"/runs/{run_id}", headers=headers).status_code == 204

    after = client.get(f"/planned-workouts/{planned['id']}", headers=headers).json()
    assert after["run_id"] is None
    assert after["status"] == "completed"


def test_other_users_cannot_complete_my_planned_run():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")
    planned = plan_run(alice).json()

    assert complete(bob, planned["id"], duration_seconds=3000).status_code == 404
    assert runs_of(bob) == []


def test_the_calendar_shows_the_kind_and_distance_and_counts_runs_in_the_summary():
    headers = register_and_login(client)
    plan_run(headers, day="2026-10-06", distance=10)
    client.post(
        "/planned-workouts/", headers=headers,
        json={"scheduled_date": "2026-10-06", "name": "Pierna"},
    )

    result = client.get(
        "/calendar/activity?start_date=2026-10-05&end_date=2026-10-11"
        "&today=2026-10-05",
        headers=headers,
    ).json()
    plans = next(d for d in result["days"] if d["date"] == "2026-10-06")["planned_workouts"]

    assert [(p["kind"], p["target_distance_km"]) for p in plans] == [
        ("run", 10.0), ("workout", None),
    ]
    assert result["plan_summary"]["total"] == 2


def test_copying_a_week_keeps_kind_and_distance_without_mixing_kinds():
    headers = register_and_login(client)
    plan_run(headers, day="2026-10-05", distance=10, name="Largo")
    client.post(
        "/planned-workouts/", headers=headers,
        json={"scheduled_date": "2026-10-05", "name": "Largo"},
    )

    copied = client.post(
        "/planned-workouts/copy-week", headers=headers,
        json={"source_start": "2026-10-05", "target_start": "2026-10-12"},
    ).json()
    in_target = client.get(
        "/planned-workouts/?start_date=2026-10-12&end_date=2026-10-18",
        headers=headers,
    ).json()

    assert copied == {"copied": 2, "skipped": 0}
    assert sorted((p["kind"], p["target_distance_km"]) for p in in_target) == [
        ("run", 10.0), ("workout", None),
    ]
    assert all(p["status"] == "planned" and p["run_id"] is None for p in in_target)


def upload(headers, data):
    return client.post(
        "/restores/account",
        headers=headers,
        files={"file": ("export.json", BytesIO(json.dumps(data).encode()), "application/json")},
        data={"password": PASSWORD},
    )


def test_export_and_restore_keep_planned_runs_and_relink_the_run():
    headers = register_and_login(client)
    open_run = plan_run(headers, day="2026-10-12", distance=21.1, name="Media").json()
    done = plan_run(headers, day="2026-10-06", distance=10).json()
    complete(headers, done["id"], duration_seconds=3000)

    exported = client.get("/exports/fitness-tracker.json", headers=headers).json()

    assert exported["format_version"] == 3
    kinds = {p["name"]: p for p in exported["planned_workouts"]}
    assert kinds["Media"]["kind"] == "run"
    assert kinds["Media"]["target_distance_km"] == 21.1
    assert kinds["Carrera"]["run_id"] == exported["runs"][0]["id"]

    # Se estropea todo y se restaura.
    with get_connection() as connection:
        connection.execute("DELETE FROM planned_workouts")
        connection.execute("DELETE FROM runs")

    assert upload(headers, exported).status_code == 200

    restored = {
        p["name"]: p
        for p in client.get("/planned-workouts/", headers=headers).json()
    }
    new_run_id = runs_of(headers)[0]["id"]

    assert restored["Media"]["kind"] == "run"
    assert restored["Media"]["target_distance_km"] == 21.1
    assert restored["Media"]["run_id"] is None
    assert restored["Carrera"]["status"] == "completed"
    assert restored["Carrera"]["run_id"] == new_run_id
    assert open_run["id"] != restored["Media"]["id"]    # ids nuevos


def test_old_exports_without_kind_restore_as_gym_sessions():
    headers = register_and_login(client)
    old_export = {
        "exported_at": "2026-01-01T00:00:00", "format_version": 2,
        "planned_workouts": [
            {
                "id": 7, "scheduled_date": "2026-01-05", "name": "Pierna",
                "notes": None, "status": "planned",
                "workout_template_id": None, "workout_session_id": None,
            }
        ],
    }

    assert upload(headers, old_export).status_code == 200

    restored = client.get("/planned-workouts/", headers=headers).json()
    assert [(p["name"], p["kind"], p["target_distance_km"]) for p in restored] == [
        ("Pierna", "workout", None),
    ]


def test_restore_rejects_an_unknown_kind_without_changing_anything():
    headers = register_and_login(client)
    plan_run(headers)
    bad = {
        "exported_at": "x", "format_version": 3,
        "planned_workouts": [
            {"scheduled_date": "2026-01-05", "name": "X", "notes": None,
             "status": "planned", "kind": "swim"},
        ],
    }

    assert upload(headers, bad).status_code == 400
    assert len(client.get("/planned-workouts/", headers=headers).json()) == 1
