import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.db import get_connection
from app.main import app
from app.services.exports import create_data_export
from tests.conftest import register_and_login
from tests.test_exports import insert_full_user_data


client = TestClient(app)
PASSWORD = "password-segura-123"


def user_id_of(email):
    with get_connection() as connection:
        return connection.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()["id"]


def strip_ids(value):
    """Los ids cambian al restaurar; el resto debe ser idéntico."""
    if isinstance(value, dict):
        return {
            key: strip_ids(item)
            for key, item in value.items()
            if key not in {"id", "exported_at"}
            and not key.endswith("_id")
        }

    if isinstance(value, list):
        return [strip_ids(item) for item in value]

    return value


def export_of(user_id, tmp_path):
    path = create_data_export(user_id=user_id, exports_dir=tmp_path)
    return json.loads(path.read_text(encoding="utf-8"))


def upload(headers, data, password=PASSWORD, filename="export.json"):
    content = data if isinstance(data, bytes) else json.dumps(data).encode()

    return client.post(
        "/restores/account",
        headers=headers,
        files={"file": (filename, BytesIO(content), "application/json")},
        data={"password": password},
    )


def count_rows(table):
    with get_connection() as connection:
        return connection.execute(
            f"SELECT COUNT(*) AS total FROM {table}"
        ).fetchone()["total"]


def test_roundtrip_restores_every_section(tmp_path):
    headers = register_and_login(client, email="alice@example.com")
    alice = user_id_of("alice@example.com")

    # Datos completos de Alice colgados de su cuenta real.
    with get_connection() as connection:
        other = insert_full_user_data(
            connection, email="seed@example.com", label="alice",
        )
        connection.execute("UPDATE users SET id = id WHERE id = ?", (other,))
        # Reasigna las filas raíz de "seed" a Alice.
        for table in (
            "daily_logs", "daily_recovery_logs", "body_metrics", "runs",
            "workout_sessions", "nutrition_days", "fitness_goals",
            "body_composition_goals", "workout_templates", "planned_workouts",
            "food_library", "meal_templates",
        ):
            connection.execute(
                f"UPDATE {table} SET user_id = ? WHERE user_id = ?",
                (alice, other),
            )

    original = export_of(alice, tmp_path)
    assert original["planned_workouts"] and original["meal_templates"]

    # Se estropea todo y se restaura.
    with get_connection() as connection:
        for table in (
            "daily_logs", "runs", "workout_sessions", "workout_templates",
            "food_library", "meal_templates", "planned_workouts",
            "nutrition_days", "fitness_goals", "body_metrics",
            "daily_recovery_logs", "body_composition_goals",
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE user_id = ?", (alice,)
            )

    response = upload(headers, original)

    assert response.status_code == 200, response.text
    restored = export_of(alice, tmp_path)
    assert strip_ids(restored) == strip_ids(original)

    # Las relaciones se reasignan a los ids nuevos.
    planned = restored["planned_workouts"][0]
    assert planned["workout_template_id"] == restored["workout_templates"][0]["id"]
    assert planned["workout_session_id"] == restored["workout_sessions"][0]["id"]


def test_restore_replaces_current_data_and_leaves_other_users_alone(tmp_path):
    headers = register_and_login(client, email="alice@example.com")
    alice = user_id_of("alice@example.com")
    register_and_login(client, email="bob@example.com")
    bob = user_id_of("bob@example.com")

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO daily_logs (user_id, date, steps, notes) "
            "VALUES (?, '2026-01-01', 111, 'antiguo')", (alice,),
        )
        connection.execute(
            "INSERT INTO daily_logs (user_id, date, steps, notes) "
            "VALUES (?, '2026-01-01', 999, 'de-bob')", (bob,),
        )
        connection.execute(
            "INSERT INTO runs (user_id, date, distance_km, duration_seconds, "
            "average_pace_seconds_km) VALUES (?, '2026-01-02', 5, 1500, 300)",
            (alice,),
        )

    backup = {
        "exported_at": "2026-02-01T10:00:00",
        "daily_logs": [{"date": "2026-02-01", "steps": 5000, "notes": "nuevo"}],
    }

    response = upload(headers, backup)

    assert response.status_code == 200, response.text
    assert response.json()["restored"] == {"daily_logs": 1}

    data = export_of(alice, tmp_path)
    assert [log["notes"] for log in data["daily_logs"]] == ["nuevo"]
    # La sección ausente (runs) no se toca.
    assert len(data["runs"]) == 1

    bob_data = export_of(bob, tmp_path)
    assert [log["notes"] for log in bob_data["daily_logs"]] == ["de-bob"]


def test_present_but_empty_section_clears_it(tmp_path):
    headers = register_and_login(client, email="alice@example.com")
    alice = user_id_of("alice@example.com")

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO daily_logs (user_id, date, steps) "
            "VALUES (?, '2026-01-01', 1)", (alice,),
        )

    response = upload(
        headers, {"exported_at": "x", "format_version": 2, "daily_logs": []},
    )

    assert response.status_code == 200, response.text
    assert export_of(alice, tmp_path)["daily_logs"] == []


def test_wrong_password_changes_nothing(tmp_path):
    headers = register_and_login(client, email="alice@example.com")
    alice = user_id_of("alice@example.com")

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO daily_logs (user_id, date, steps) "
            "VALUES (?, '2026-01-01', 1)", (alice,),
        )

    response = upload(
        headers,
        {"exported_at": "x", "daily_logs": []},
        password="incorrecta-123",
    )

    assert response.status_code == 400
    assert len(export_of(alice, tmp_path)["daily_logs"]) == 1


def test_invalid_data_rolls_back_everything(tmp_path):
    headers = register_and_login(client, email="alice@example.com")
    alice = user_id_of("alice@example.com")

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO daily_logs (user_id, date, steps, notes) "
            "VALUES (?, '2026-01-01', 1, 'conservar')", (alice,),
        )
        connection.execute(
            "INSERT INTO runs (user_id, date, distance_km, duration_seconds, "
            "average_pace_seconds_km) VALUES (?, '2026-01-02', 5, 1500, 300)",
            (alice,),
        )

    broken = {
        "exported_at": "x",
        "daily_logs": [{"date": "2026-03-01", "steps": 1}],
        # La distancia negativa viola un CHECK de la base de datos.
        "runs": [{
            "date": "2026-03-01", "distance_km": -5,
            "duration_seconds": 100, "average_pace_seconds_km": 300,
        }],
    }

    response = upload(headers, broken)

    assert response.status_code == 400, response.text
    data = export_of(alice, tmp_path)
    assert [log["notes"] for log in data["daily_logs"]] == ["conservar"]
    assert len(data["runs"]) == 1


def test_duplicate_dates_in_the_file_are_rejected(tmp_path):
    headers = register_and_login(client, email="alice@example.com")
    alice = user_id_of("alice@example.com")

    response = upload(headers, {
        "exported_at": "x",
        "daily_logs": [
            {"date": "2026-03-01", "steps": 1},
            {"date": "2026-03-01", "steps": 2},
        ],
    })

    assert response.status_code == 400
    assert export_of(alice, tmp_path)["daily_logs"] == []


def test_invalid_files_are_rejected():
    headers = register_and_login(client, email="alice@example.com")

    assert upload(headers, b"no es json").status_code == 400
    assert upload(headers, [1, 2, 3]).status_code == 400
    assert upload(headers, {"daily_logs": []}).status_code == 400  # sin exported_at
    assert upload(headers, {"exported_at": "x"}).status_code == 400  # sin datos
    assert upload(
        headers, {"exported_at": "x", "format_version": 99, "runs": []}
    ).status_code == 400
    assert upload(
        headers, {"exported_at": "x", "daily_logs": "mal"}
    ).status_code == 400
    assert upload(
        headers,
        {"exported_at": "x", "daily_logs": [{"date": "no-fecha", "steps": 1}]},
    ).status_code == 400
    assert upload(
        headers, {"exported_at": "x", "runs": []}, filename="copia.db"
    ).status_code == 400


def test_requires_authentication():
    response = client.post(
        "/restores/account",
        files={"file": ("e.json", BytesIO(b"{}"), "application/json")},
        data={"password": PASSWORD},
    )

    assert response.status_code == 401
