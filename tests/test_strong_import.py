from io import BytesIO

from fastapi.testclient import TestClient

from app.db import get_connection
from app.main import app
from tests.conftest import register_and_login


client = TestClient(app)

HEADER = (
    "Date,Workout Name,Duration,Exercise Name,Set Order,Weight,Reps,"
    "Distance,Seconds,Notes,Workout Notes,RPE"
)

SAMPLE = "\n".join([
    HEADER,
    '2023-10-18 18:03:00,Pierna,1h 7m,Squat (Barbell),W,40,10,0,0,Controlar,Buen dia,',
    '2023-10-18 18:03:00,Pierna,1h 7m,Squat (Barbell),1,100,5,0,0,Controlar,Buen dia,8.5',
    '2023-10-18 18:03:00,Pierna,1h 7m,Squat (Barbell),2,100,4,0,0,Controlar,Buen dia,10',
    '2023-10-18 18:03:00,Pierna,1h 7m,Squat (Barbell),Rest Timer,0,0,0,120,,,',
    '2023-10-18 18:03:00,Pierna,1h 7m,Leg Press,D,150,12,0,0,,Buen dia,',
    '2023-10-18 18:03:00,Pierna,1h 7m,Leg Press,F,150,6,0,0,,Buen dia,',
    '2023-10-20 09:00:00,Empuje,45m,Bench Press (Barbell),1,80,8,0,0,,,',
]) + "\n"


def upload(headers, content, unit="kg", dry_run=True, filename="strong.csv"):
    data = content.encode() if isinstance(content, str) else content

    return client.post(
        "/imports/strong",
        headers=headers,
        files={"file": (filename, BytesIO(data), "text/csv")},
        data={"weight_unit": unit, "dry_run": "true" if dry_run else "false"},
    )


def sets_of(session_name):
    with get_connection() as connection:
        return connection.execute(
            "SELECT e.name AS exercise, s.set_type, s.position, "
            "s.repetitions, s.weight_kg, s.rir, s.notes "
            "FROM workout_sets s "
            "JOIN workout_exercises e ON e.id = s.workout_exercise_id "
            "JOIN workout_sessions w ON w.id = e.workout_session_id "
            "WHERE w.name = ? ORDER BY e.position, s.position",
            (session_name,),
        ).fetchall()


def count(table):
    with get_connection() as connection:
        return connection.execute(
            f"SELECT COUNT(*) AS total FROM {table}"
        ).fetchone()["total"]


def test_requires_authentication():
    response = client.post(
        "/imports/strong",
        files={"file": ("s.csv", BytesIO(SAMPLE.encode()), "text/csv")},
    )

    assert response.status_code == 401


def test_dry_run_counts_and_saves_nothing():
    headers = register_and_login(client)

    result = upload(headers, SAMPLE).json()

    assert result["dry_run"] is True
    assert result["sessions"] == 2
    assert result["exercises"] == 3
    assert result["sets"] == 6          # sin la fila «Rest Timer»
    assert result["omitted_sets"] == 0  # el descanso no cuenta como omitida
    assert count("workout_sessions") == 0


def test_import_maps_set_orders_and_rpe():
    headers = register_and_login(client)

    assert upload(headers, SAMPLE, dry_run=False).status_code == 200

    squat = sets_of("Pierna")

    assert [(s["exercise"], s["set_type"]) for s in squat] == [
        ("Squat (Barbell)", "warmup"),
        ("Squat (Barbell)", "working"),
        ("Squat (Barbell)", "working"),
        ("Leg Press", "drop_set"),
        ("Leg Press", "working"),
    ]
    assert squat[1]["rir"] == 1.5
    assert squat[2]["rir"] == 0
    assert squat[4]["notes"] == "Al fallo"

    sessions = client.get("/workout-sessions", headers=headers).json()
    leg_day = next(item for item in sessions if item["name"] == "Pierna")

    assert leg_day["date"] == "2023-10-18"
    assert leg_day["notes"] == "Buen dia"


def test_weight_unit_is_applied():
    headers = register_and_login(client)
    csv_text = (
        HEADER + "\n"
        "2023-11-01 10:00:00,Pecho,30m,Bench Press,1,225,5,0,0,,,\n"
    )

    upload(headers, csv_text, unit="lb", dry_run=False)

    assert abs(sets_of("Pecho")[0]["weight_kg"] - 102.058) < 0.01


def test_default_unit_is_kilograms():
    headers = register_and_login(client)
    csv_text = (
        HEADER + "\n"
        "2023-11-01 10:00:00,Pecho,30m,Bench Press,1,100,5,0,0,,,\n"
    )

    client.post(
        "/imports/strong",
        headers=headers,
        files={"file": ("s.csv", BytesIO(csv_text.encode()), "text/csv")},
        data={"dry_run": "false"},
    )

    assert sets_of("Pecho")[0]["weight_kg"] == 100


def test_invalid_unit_is_rejected_without_saving():
    headers = register_and_login(client)

    response = upload(headers, SAMPLE, unit="stone", dry_run=False)

    assert response.status_code == 400
    assert count("workout_sessions") == 0


def test_repeating_the_import_does_not_duplicate_sessions():
    headers = register_and_login(client)

    upload(headers, SAMPLE, dry_run=False)
    second = upload(headers, SAMPLE, dry_run=False).json()

    assert second["sessions"] == 0
    assert second["skipped_sessions"] == 2
    assert count("workout_sessions") == 2


def test_import_only_touches_the_authenticated_account():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")

    upload(alice, SAMPLE, dry_run=False)

    assert upload(bob, SAMPLE, dry_run=False).json()["sessions"] == 2
    assert len(client.get("/workout-sessions", headers=bob).json()) == 2


def test_invalid_files_are_rejected_without_saving_anything():
    headers = register_and_login(client)
    bad_date = HEADER + "\nfecha-rara,Pierna,1h,Squat,1,100,5,0,0,,,\n"
    # Un CSV de Hevy no es un CSV de Strong, y viceversa.
    hevy_csv = "title,start_time,exercise_title,set_type,weight_kg,reps\n"
    cases = {
        "nada.csv": "esto no es un csv",
        "hevy.csv": hevy_csv,
        "fecha.csv": bad_date,
        "binario.csv": b"\xff\xfe\x00\x00",
        "datos.json": SAMPLE,
    }

    for name, content in cases.items():
        response = upload(headers, content, dry_run=False, filename=name)

        assert response.status_code == 400, name

    assert count("workout_sessions") == 0


def test_sets_without_repetitions_are_omitted_with_a_warning():
    headers = register_and_login(client)
    csv_text = (
        HEADER + "\n"
        "2023-11-05 07:00:00,Cardio,30m,Treadmill,1,0,0,5,1800,,,\n"
        "2023-11-05 07:00:00,Cardio,30m,Plank,1,0,60,0,0,,,\n"
    )

    result = upload(headers, csv_text, dry_run=False).json()

    assert result["sets"] == 1
    assert result["omitted_sets"] == 1
    assert any("Treadmill" in warning for warning in result["warnings"])
