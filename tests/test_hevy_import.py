from io import BytesIO

from fastapi.testclient import TestClient

from app.db import get_connection
from app.main import app
from app.services.hevy_import import parse_workout_date
from tests.conftest import register_and_login


client = TestClient(app)

HEADER = (
    "title,start_time,end_time,description,exercise_title,superset_id,"
    "exercise_notes,set_index,set_type,weight_kg,reps,distance_km,"
    "duration_seconds,rpe"
)

# Dos entrenos; el primero con calentamiento, serie normal, al fallo y drop set.
SAMPLE = "\n".join([
    HEADER,
    'Pierna,"18 Oct 2023, 18:03","18 Oct 2023, 19:10",Buen dia,'
    'Squat (Barbell),,Controlar bajada,0,warmup,40,10,,,',
    'Pierna,"18 Oct 2023, 18:03","18 Oct 2023, 19:10",Buen dia,'
    'Squat (Barbell),,Controlar bajada,1,normal,100,5,,,8.5',
    'Pierna,"18 Oct 2023, 18:03","18 Oct 2023, 19:10",Buen dia,'
    'Squat (Barbell),,Controlar bajada,2,failure,100,4,,,10',
    'Pierna,"18 Oct 2023, 18:03","18 Oct 2023, 19:10",Buen dia,'
    'Leg Press,,,0,dropset,150,12,,,',
    'Empuje,"20 Oct 2023, 09:00","20 Oct 2023, 10:00",,'
    'Bench Press (Barbell),,,0,normal,80,8,,,',
]) + "\n"


def upload(headers, content, dry_run=True, filename="workout_data.csv"):
    data = content.encode() if isinstance(content, str) else content

    return client.post(
        "/imports/hevy",
        headers=headers,
        files={"file": (filename, BytesIO(data), "text/csv")},
        data={"dry_run": "true" if dry_run else "false"},
    )


def count(table):
    with get_connection() as connection:
        return connection.execute(
            f"SELECT COUNT(*) AS total FROM {table}"
        ).fetchone()["total"]


def test_requires_authentication():
    response = client.post(
        "/imports/hevy",
        files={"file": ("w.csv", BytesIO(SAMPLE.encode()), "text/csv")},
    )

    assert response.status_code == 401


def test_dry_run_reports_what_would_happen_and_saves_nothing():
    headers = register_and_login(client)

    response = upload(headers, SAMPLE, dry_run=True)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["dry_run"] is True
    assert result["sessions"] == 2
    assert result["exercises"] == 3
    assert result["sets"] == 5
    assert result["skipped_sessions"] == 0
    assert count("workout_sessions") == 0


def test_import_creates_sessions_exercises_and_sets_with_mapped_types():
    headers = register_and_login(client)

    response = upload(headers, SAMPLE, dry_run=False)

    assert response.status_code == 200, response.text
    assert response.json()["sessions"] == 2

    sessions = client.get("/workout-sessions", headers=headers).json()
    leg_day = next(item for item in sessions if item["name"] == "Pierna")

    assert leg_day["date"] == "2023-10-18"
    assert leg_day["notes"] == "Buen dia"

    with get_connection() as connection:
        sets = connection.execute(
            "SELECT e.name AS exercise, e.muscle_group, e.technique_notes, "
            "e.position AS exercise_position, s.set_type, s.position, "
            "s.repetitions, s.weight_kg, s.rir, s.notes "
            "FROM workout_sets s "
            "JOIN workout_exercises e ON e.id = s.workout_exercise_id "
            "JOIN workout_sessions w ON w.id = e.workout_session_id "
            "WHERE w.name = 'Pierna' "
            "ORDER BY e.position, s.position"
        ).fetchall()

    assert [(s["exercise"], s["set_type"], s["position"]) for s in sets] == [
        ("Squat (Barbell)", "warmup", 1),
        ("Squat (Barbell)", "working", 2),
        ("Squat (Barbell)", "working", 3),
        ("Leg Press", "drop_set", 1),
    ]
    assert sets[1]["repetitions"] == 5 and sets[1]["weight_kg"] == 100
    assert sets[1]["rir"] == 1.5          # RPE 8,5 -> RIR 1,5
    assert sets[2]["rir"] == 0            # RPE 10 -> RIR 0
    assert sets[2]["notes"] == "Al fallo"
    assert sets[0]["technique_notes"] == "Controlar bajada"
    assert sets[0]["muscle_group"] == "Sin clasificar"
    assert [s["exercise_position"] for s in sets] == [1, 1, 1, 2]


def test_importing_the_same_file_twice_does_not_duplicate_sessions():
    headers = register_and_login(client)

    upload(headers, SAMPLE, dry_run=False)
    second = upload(headers, SAMPLE, dry_run=False)

    assert second.status_code == 200
    assert second.json()["sessions"] == 0
    assert second.json()["skipped_sessions"] == 2
    assert count("workout_sessions") == 2


def test_import_only_touches_the_authenticated_account():
    alice = register_and_login(client, email="alice@example.com")
    bob = register_and_login(client, email="bob@example.com")

    upload(alice, SAMPLE, dry_run=False)

    # Bob no tiene esas sesiones: su importación no se considera repetida.
    result = upload(bob, SAMPLE, dry_run=False).json()

    assert result["sessions"] == 2
    assert count("workout_sessions") == 4
    assert len(client.get("/workout-sessions", headers=bob).json()) == 2


def test_import_adds_to_existing_data_without_deleting_it():
    headers = register_and_login(client)
    client.post(
        "/workout-sessions",
        headers=headers,
        json={"date": "2023-10-01", "name": "Mi sesion"},
    )

    upload(headers, SAMPLE, dry_run=False)

    names = {s["name"] for s in client.get("/workout-sessions", headers=headers).json()}
    assert names == {"Mi sesion", "Pierna", "Empuje"}


def test_pounds_are_converted_to_kilograms():
    headers = register_and_login(client)
    csv_text = (
        "title,start_time,exercise_title,set_type,weight_lbs,reps\n"
        'Pecho,"01 Nov 2023, 10:00",Bench Press,normal,225,5\n'
    )

    assert upload(headers, csv_text, dry_run=False).status_code == 200

    with get_connection() as connection:
        weight = connection.execute(
            "SELECT weight_kg FROM workout_sets"
        ).fetchone()["weight_kg"]

    assert abs(weight - 102.058) < 0.01


def test_sets_without_repetitions_are_omitted_with_a_warning():
    headers = register_and_login(client)
    csv_text = "\n".join([
        HEADER,
        'Cardio,"05 Nov 2023, 07:00",,,Treadmill,,,0,normal,,,5,1800,',
        'Cardio,"05 Nov 2023, 07:00",,,Plank,,,0,normal,0,60,,,',
        'Solo cardio,"06 Nov 2023, 07:00",,,Bike,,,0,normal,,,10,2400,',
    ]) + "\n"

    result = upload(headers, csv_text, dry_run=False).json()

    assert result["sessions"] == 1          # «Solo cardio» no tiene series válidas
    assert result["sets"] == 1
    assert result["omitted_sets"] == 2
    assert any("Treadmill" in warning for warning in result["warnings"])
    assert any("Solo cardio" in warning for warning in result["warnings"])


def test_invalid_files_are_rejected_without_saving_anything():
    headers = register_and_login(client)
    bad_date = HEADER + '\nPierna,fecha-rara,,,Squat,,,0,normal,100,5,,,\n'
    cases = {
        "not-csv.csv": "esto no es un csv de hevy",
        "missing-columns.csv": "a,b\n1,2\n",
        "bad-date.csv": bad_date,
        "binary.csv": b"\xff\xfe\x00\x00",
    }

    for name, content in cases.items():
        response = upload(headers, content, dry_run=False, filename=name)

        assert response.status_code == 400, name

    assert count("workout_sessions") == 0


def test_bad_row_does_not_save_the_rest_of_the_file():
    headers = register_and_login(client)
    csv_text = SAMPLE + 'Roto,no-fecha,,,Squat,,,0,normal,100,5,,,\n'

    response = upload(headers, csv_text, dry_run=False)

    assert response.status_code == 400
    assert "fila" in response.json()["detail"]
    assert count("workout_sessions") == 0


def test_only_csv_files_under_the_size_limit_are_accepted():
    headers = register_and_login(client)

    wrong_type = upload(headers, SAMPLE, filename="datos.json")
    too_big = upload(headers, b"x" * (10 * 1024 * 1024 + 1))

    assert wrong_type.status_code == 400
    assert too_big.status_code == 413


def test_semicolon_delimited_and_bom_files_are_accepted():
    headers = register_and_login(client)
    csv_text = "﻿" + SAMPLE.replace(",", ";")

    # Las comas dentro de las fechas entre comillas se mantienen con «;».
    csv_text = csv_text.replace('"18 Oct 2023; 18:03"', '"18 Oct 2023, 18:03"')
    csv_text = csv_text.replace('"18 Oct 2023; 19:10"', '"18 Oct 2023, 19:10"')
    csv_text = csv_text.replace('"20 Oct 2023; 09:00"', '"20 Oct 2023, 09:00"')
    csv_text = csv_text.replace('"20 Oct 2023; 10:00"', '"20 Oct 2023, 10:00"')

    response = upload(headers, csv_text, dry_run=True)

    assert response.status_code == 200, response.text
    assert response.json()["sessions"] == 2


def test_workout_date_parsing():
    assert parse_workout_date("18 Oct 2023, 18:03") == "2023-10-18"
    assert parse_workout_date("5 Jan 2024, 07:00") == "2024-01-05"
    assert parse_workout_date("2023-10-18 18:03:00") == "2023-10-18"
    assert parse_workout_date("2023-10-18T18:03:00Z") == "2023-10-18"
    assert parse_workout_date("31 Feb 2023, 10:00") is None
    assert parse_workout_date("nunca") is None
