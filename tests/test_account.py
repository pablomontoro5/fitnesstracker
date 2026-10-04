from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.db import get_connection
from app.main import app
from app.password_resets import create_password_reset
from app.security import hash_password
from tests.conftest import register_and_login
from tests.db_helpers import foreign_keys, table_columns, table_names
from tests.test_exports import insert_full_user_data


client = TestClient(app)

PASSWORD = "password-segura-123"
NEW_PASSWORD = "otra-contrasena-larga-456"


def get_user_id(email: str) -> int:
    with get_connection() as connection:
        return connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()["id"]


def make_reset_code(email: str, **kwargs) -> str:
    with get_connection() as connection:
        code, _ = create_password_reset(
            connection,
            get_user_id(email),
            **kwargs,
        )

    return code


def login(email: str, password: str):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def reset(email: str, code: str, new_password: str = NEW_PASSWORD):
    return client.post(
        "/auth/reset-password",
        json={"email": email, "code": code, "new_password": new_password},
    )


# --- Cambio de contraseña -------------------------------------------------


def test_change_password_replaces_the_password_and_closes_other_sessions():
    old_headers = register_and_login(client, email="a@example.com")

    response = client.post(
        "/auth/change-password",
        headers=old_headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 200
    new_headers = {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }

    # El token anterior ya no vale; el nuevo, sí.
    assert client.get("/auth/me", headers=old_headers).status_code == 401
    assert client.get("/auth/me", headers=new_headers).status_code == 200

    assert login("a@example.com", PASSWORD).status_code == 401
    assert login("a@example.com", NEW_PASSWORD).status_code == 200


def test_change_password_rejects_a_wrong_current_password_without_logging_out():
    headers = register_and_login(client, email="a@example.com")

    response = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "no-es-esta-1234", "new_password": NEW_PASSWORD},
    )

    # 400 y no 401: un 401 haría que la interfaz cerrara la sesión.
    assert response.status_code == 400
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert login("a@example.com", PASSWORD).status_code == 200


def test_change_password_requires_a_different_and_long_enough_password():
    headers = register_and_login(client, email="a@example.com")

    same = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": PASSWORD},
    )
    short = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "corta"},
    )

    assert same.status_code == 400
    assert short.status_code == 422


def test_change_password_requires_authentication():
    response = client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 401


def test_wrong_current_passwords_are_rate_limited():
    headers = register_and_login(client, email="a@example.com")
    payload = {"current_password": "no-es-esta-1234", "new_password": NEW_PASSWORD}

    statuses = [
        client.post("/auth/change-password", headers=headers, json=payload).status_code
        for _ in range(6)
    ]

    assert statuses == [400, 400, 400, 400, 400, 429]

    blocked = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


# --- Recuperación con código ---------------------------------------------


def test_reset_password_with_a_valid_code_sets_the_new_password():
    old_headers = register_and_login(client, email="a@example.com")
    code = make_reset_code("a@example.com")

    response = reset("a@example.com", code)

    assert response.status_code == 204
    assert login("a@example.com", PASSWORD).status_code == 401
    assert login("a@example.com", NEW_PASSWORD).status_code == 200
    # Las sesiones abiertas antes de recuperar la cuenta dejan de valer.
    assert client.get("/auth/me", headers=old_headers).status_code == 401


def test_reset_code_works_only_once():
    register_and_login(client, email="a@example.com")
    code = make_reset_code("a@example.com")

    assert reset("a@example.com", code).status_code == 204
    assert reset("a@example.com", code, "tercera-contrasena-789").status_code == 400
    assert login("a@example.com", NEW_PASSWORD).status_code == 200


def test_reset_is_case_insensitive_on_email_and_ignores_surrounding_spaces():
    register_and_login(client, email="a@example.com")
    code = make_reset_code("a@example.com")

    assert reset("  A@Example.com ", f" {code} ").status_code == 204


def test_reset_gives_the_same_error_for_every_kind_of_failure():
    register_and_login(client, email="a@example.com")
    register_and_login(client, email="b@example.com")
    code_for_a = make_reset_code("a@example.com")
    expired = make_reset_code(
        "b@example.com",
        now=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    failures = [
        reset("a@example.com", "codigo-inventado"),
        reset("nadie@example.com", code_for_a),
        reset("b@example.com", code_for_a),  # código de otra cuenta
        reset("b@example.com", expired),
    ]

    assert {response.status_code for response in failures} == {400}
    assert len({response.json()["detail"] for response in failures}) == 1
    assert login("a@example.com", PASSWORD).status_code == 200
    assert login("b@example.com", PASSWORD).status_code == 200


def test_a_new_reset_code_cancels_the_previous_one():
    register_and_login(client, email="a@example.com")
    first = make_reset_code("a@example.com")
    second = make_reset_code("a@example.com")

    assert reset("a@example.com", first).status_code == 400
    assert reset("a@example.com", second).status_code == 204


def test_reset_requires_a_long_enough_password():
    register_and_login(client, email="a@example.com")
    code = make_reset_code("a@example.com")

    assert reset("a@example.com", code, "corta").status_code == 422
    # La petición inválida no gasta el código.
    assert reset("a@example.com", code).status_code == 204


def test_deactivated_accounts_cannot_be_recovered():
    register_and_login(client, email="a@example.com")
    code = make_reset_code("a@example.com")

    with get_connection() as connection:
        connection.execute("UPDATE users SET is_active = 0")

    assert reset("a@example.com", code).status_code == 400


def test_reset_attempts_are_rate_limited_per_ip():
    statuses = [
        reset("nadie@example.com", f"codigo-{number}").status_code
        for number in range(11)
    ]

    assert statuses == [400] * 10 + [429]


def test_reset_clears_a_login_lockout_for_that_account():
    register_and_login(client, email="a@example.com")

    for _ in range(5):
        assert login("a@example.com", "mala-contrasena-123").status_code == 401

    assert login("a@example.com", PASSWORD).status_code == 429

    assert reset("a@example.com", make_reset_code("a@example.com")).status_code == 204
    assert login("a@example.com", NEW_PASSWORD).status_code == 200


def test_cli_creates_a_reset_code_that_works(capsys):
    register_and_login(client, email="a@example.com")

    assert cli_main(["create-reset-code", "--email", "A@example.com"]) == 0

    output = capsys.readouterr().out
    code = output.split("Código de recuperación: ")[1].splitlines()[0]

    assert reset("a@example.com", code).status_code == 204


def test_cli_reports_an_unknown_email(capsys):
    assert cli_main(["create-reset-code", "--email", "nadie@example.com"]) == 1
    assert "No existe ninguna cuenta" in capsys.readouterr().err


def test_reset_codes_are_stored_hashed():
    register_and_login(client, email="a@example.com")
    code = make_reset_code("a@example.com")

    with get_connection() as connection:
        stored = [
            row["code_hash"]
            for row in connection.execute("SELECT code_hash FROM password_resets")
        ]

    assert stored and code not in stored


# --- Borrado de cuenta ----------------------------------------------------


def delete_account(headers, password: str):
    return client.request(
        "DELETE",
        "/auth/me",
        headers=headers,
        json={"password": password},
    )


def test_delete_account_requires_the_right_password():
    headers = register_and_login(client, email="a@example.com")

    response = delete_account(headers, "no-es-esta-1234")

    assert response.status_code == 400
    assert client.get("/auth/me", headers=headers).status_code == 200


def test_delete_account_requires_authentication():
    response = client.request("DELETE", "/auth/me", json={"password": PASSWORD})

    assert response.status_code == 401


def test_delete_account_removes_the_user_and_all_their_data_only():
    headers = register_and_login(client, email="a@example.com")

    with get_connection() as connection:
        deleted_id = get_user_id("a@example.com")
        # Se siembran datos completos para la cuenta que se va a borrar...
        connection.execute("DELETE FROM users WHERE id = ?", (deleted_id,))
        deleted_id = insert_full_user_data(
            connection, email="a@example.com", label="borrada"
        )
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(PASSWORD), deleted_id),
        )
        # ...y para otra que debe quedar intacta.
        kept_id = insert_full_user_data(
            connection, email="b@example.com", label="conservada"
        )

    headers = {
        "Authorization": (
            f"Bearer {login('a@example.com', PASSWORD).json()['access_token']}"
        )
    }

    assert delete_account(headers, PASSWORD).status_code == 204

    with get_connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE id = ?", (deleted_id,)
        ).fetchone()["total"] == 0
        assert connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE id = ?", (kept_id,)
        ).fetchone()["total"] == 1

        for table in table_names(connection):
            columns = table_columns(connection, table)

            if "user_id" in columns:
                leftovers = connection.execute(
                    f"SELECT COUNT(*) AS total FROM {table} WHERE user_id = ?",
                    (deleted_id,),
                ).fetchone()["total"]
                assert leftovers == 0, table

        # Las tablas hijas (series, ejercicios, comidas...) tampoco conservan
        # filas de la cuenta borrada: solo quedan las de la otra cuenta.
        for table, expected in (
            ("workout_exercises", 1),
            ("workout_sets", 1),
            ("nutrition_meals", 1),
            ("nutrition_foods", 1),
        ):
            assert connection.execute(
                f"SELECT COUNT(*) AS total FROM {table}"
            ).fetchone()["total"] == expected, table


    assert login("a@example.com", PASSWORD).status_code == 401
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_every_table_is_reachable_from_users_through_cascades():
    """Garantía estructural: una tabla nueva sin CASCADE falla aquí.

    Cada tabla debe tener user_id con CASCADE hacia users, o colgar de otra
    tabla con CASCADE (series, ejercicios, comidas...). Así borrar la cuenta
    no deja filas huérfanas.
    """
    with get_connection() as connection:
        tables = table_names(connection)
        references = {table: foreign_keys(connection, table) for table in tables}
        columns = {table: table_columns(connection, table) for table in tables}

    for table in tables:
        for foreign_key in references[table]:
            if foreign_key["table"] != "users":
                continue

            if (table, foreign_key["from"]) == (
                "invitations",
                "used_by_user_id",
            ):
                # La invitación se conserva, sin referencia a la cuenta.
                assert foreign_key["on_delete"] == "SET NULL"
            else:
                assert foreign_key["on_delete"] == "CASCADE", (
                    table,
                    foreign_key["from"],
                )

    def cascades_from_users(table: str, seen: frozenset = frozenset()) -> bool:
        if table in seen:
            return False

        for foreign_key in references[table]:
            if foreign_key["on_delete"] != "CASCADE":
                continue

            if foreign_key["table"] == "users":
                return True

            if cascades_from_users(foreign_key["table"], seen | {table}):
                return True

        return False

    unreachable = [
        table
        for table in tables
        if table not in {"users", "invitations", "schema_migrations"}
        and not cascades_from_users(table)
    ]

    assert unreachable == []

    for table in tables:
        if "user_id" in columns[table]:
            assert any(
                fk["table"] == "users" and fk["from"] == "user_id"
                for fk in references[table]
            ), table


def test_wrong_passwords_when_deleting_are_rate_limited():
    headers = register_and_login(client, email="a@example.com")

    statuses = [
        delete_account(headers, "no-es-esta-1234").status_code
        for _ in range(6)
    ]

    assert statuses == [400, 400, 400, 400, 400, 429]
