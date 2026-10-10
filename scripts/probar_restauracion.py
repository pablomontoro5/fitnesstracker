"""Prueba la restauración de una cuenta contra la base de datos REAL.

    python scripts/probar_restauracion.py --confirmar [--env-file .env]

Qué hace (todo con usuarios desechables @restore-test.invalid):
  1. Crea dos usuarios de prueba con datos en todas las secciones.
  2. Exporta la cuenta A, le borra los datos y la restaura desde su exportación.
  3. Comprueba que la cuenta A queda igual y que la B no ha cambiado.
  4. Comprueba que una contraseña incorrecta y un archivo inválido no cambian nada.
  5. Borra los dos usuarios de prueba, pase o falle algo.

No toca a ningún otro usuario ni ejecuta migraciones. La cadena de conexión se
lee de FITNESS_TRACKER_DATABASE_URL o del .env; nunca se muestra (solo el host).
"""
import argparse
import json
import os
import secrets
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATABASE_URL_ENV = "FITNESS_TRACKER_DATABASE_URL"
TEST_DOMAIN = "restore-test.invalid"

ROOT_TABLES = (
    "daily_logs", "daily_recovery_logs", "body_metrics", "runs",
    "workout_sessions", "nutrition_days", "fitness_goals",
    "body_composition_goals", "workout_templates", "planned_workouts",
    "food_library", "meal_templates",
)


def load_env_file(path: Path) -> None:
    """Lee solo la cadena de conexión del .env (sin dependencias extra)."""
    if DATABASE_URL_ENV in os.environ or not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.strip().partition("=")

        if key.strip() == DATABASE_URL_ENV:
            os.environ[DATABASE_URL_ENV] = value.strip().strip("'\"")
            return


def diagnose_url(url: str) -> list[str]:
    """Errores típicos al montar la cadena de Supabase (sin revelar secretos)."""
    problems = []

    if "[" in url or "]" in url:
        # Con corchetes la cadena ni siquiera se puede analizar.
        return [
            "quedan corchetes: sustituye [YOUR-PASSWORD] entero, sin corchetes"
        ]

    parsed = urlparse(url)
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")

    if parsed.scheme not in {"postgresql", "postgres"}:
        problems.append("debe empezar por postgresql://")

    if url.split("://", 1)[-1].count("@") > 1:
        problems.append(
            "la contraseña tiene una @ sin codificar (escríbela como %40)"
        )

    if (parsed.hostname or "").endswith(".pooler.supabase.com") and "." not in user:
        problems.append(
            "con el pooler el usuario debe ser postgres.<id-del-proyecto>, "
            "no solo postgres"
        )

    if not password:
        problems.append("no hay contraseña en la cadena")

    return problems


def strip_ids(value):
    """Los ids cambian al restaurar; el resto debe ser idéntico."""
    if isinstance(value, dict):
        return {
            key: strip_ids(item)
            for key, item in value.items()
            if key not in {"id", "exported_at"} and not key.endswith("_id")
        }

    if isinstance(value, list):
        return [strip_ids(item) for item in value]

    return value


def seed_user(connection, email: str, label: str, password_hash: str) -> int:
    user_id = connection.execute(
        "INSERT INTO users (email, display_name, password_hash) "
        "VALUES (?, ?, ?)",
        (email, f"Prueba {label}", password_hash),
    ).lastrowid
    run = connection.execute

    run(
        "INSERT INTO daily_logs (user_id, date, steps, notes) "
        "VALUES (?, ?, ?, ?)",
        (user_id, "2026-09-07", 1000, f"pasos-{label}"),
    )
    run(
        "INSERT INTO body_metrics (user_id, date, weight_kg, height_cm, bmi, "
        "notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-09-07", 70, 175, 22.9, f"cuerpo-{label}"),
    )
    run(
        "INSERT INTO runs (user_id, date, distance_km, duration_seconds, "
        "average_pace_seconds_km, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-09-07", 5, 1500, 300, f"carrera-{label}"),
    )

    session_id = run(
        "INSERT INTO workout_sessions (user_id, date, name, notes) "
        "VALUES (?, ?, ?, ?)",
        (user_id, "2026-09-07", f"sesion-{label}", None),
    ).lastrowid
    exercise_id = run(
        "INSERT INTO workout_exercises (workout_session_id, name, "
        "muscle_group, position, technique_notes) VALUES (?, ?, ?, ?, ?)",
        (session_id, f"ejercicio-{label}", "pierna", 1, None),
    ).lastrowid
    run(
        "INSERT INTO workout_sets (workout_exercise_id, set_type, position, "
        "target_rep_range, repetitions, weight_kg, rir, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (exercise_id, "working", 1, "8-10", 8, 60, 2, f"serie-{label}"),
    )

    day_id = run(
        "INSERT INTO nutrition_days (user_id, date, notes) VALUES (?, ?, ?)",
        (user_id, "2026-09-07", f"dia-{label}"),
    ).lastrowid
    meal_id = run(
        "INSERT INTO nutrition_meals (nutrition_day_id, name, position) "
        "VALUES (?, ?, ?)",
        (day_id, f"comida-{label}", 1),
    ).lastrowid
    run(
        "INSERT INTO nutrition_foods (nutrition_meal_id, name, quantity_g, "
        "calories, protein_g, carbs_g, fat_g, position, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (meal_id, f"alimento-{label}", 100, 100, 5, 10, 1, 1, None),
    )

    run(
        "INSERT INTO daily_recovery_logs (user_id, date, sleep_minutes, "
        "sleep_quality, is_rest_day, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-09-07", 450, 4, 1, f"recuperacion-{label}"),
    )
    run(
        "INSERT INTO fitness_goals (user_id, goal_type, target_value) "
        "VALUES (?, ?, ?)",
        (user_id, "daily_steps", 9000),
    )
    run(
        "INSERT INTO body_composition_goals (user_id, metric_type, "
        "target_value, direction, start_value, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "weight_kg", 68, "decrease", 72, "2026-09-01"),
    )

    template_id = run(
        "INSERT INTO workout_templates (user_id, name, notes) "
        "VALUES (?, ?, ?)",
        (user_id, f"plantilla-{label}", None),
    ).lastrowid
    template_exercise_id = run(
        "INSERT INTO workout_template_exercises (workout_template_id, name, "
        "muscle_group, position, technique_notes) VALUES (?, ?, ?, ?, ?)",
        (template_id, f"press-{label}", "pecho", 1, None),
    ).lastrowid
    run(
        "INSERT INTO workout_template_sets (workout_template_exercise_id, "
        "set_type, position, target_rep_range, repetitions, weight_kg, rir, "
        "notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (template_exercise_id, "working", 1, "6-8", 6, 50, 2, None),
    )
    run(
        "INSERT INTO planned_workouts (user_id, scheduled_date, "
        "workout_template_id, name, notes, status, workout_session_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            user_id, "2026-09-10", template_id, f"plan-{label}", None,
            "completed", session_id,
        ),
    )

    run(
        "INSERT INTO food_library (user_id, name, calories_per_100g, "
        "protein_per_100g, carbs_per_100g, fat_per_100g, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, f"arroz-{label}", 130, 2.7, 28, 0.3, None),
    )
    meal_template_id = run(
        "INSERT INTO meal_templates (user_id, name, notes) VALUES (?, ?, ?)",
        (user_id, f"desayuno-{label}", None),
    ).lastrowid
    run(
        "INSERT INTO meal_template_items (meal_template_id, name, "
        "quantity_g, calories_per_100g, protein_per_100g, carbs_per_100g, "
        "fat_per_100g, position, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (meal_template_id, f"avena-{label}", 50, 370, 13, 60, 7, 1, None),
    )

    return user_id


def main() -> int:
    # La consola de Windows usa cp1252 y fallaría con tildes y símbolos.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--confirmar", action="store_true",
                        help="Necesario: confirma que se ejecuta contra la BD configurada.")
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    args = parser.parse_args()

    load_env_file(Path(args.env_file))
    url = os.environ.get(DATABASE_URL_ENV, "").strip()

    if not url:
        print(f"Falta {DATABASE_URL_ENV} (en el entorno o en {args.env_file}).")
        return 2

    problems = diagnose_url(url)

    try:
        parsed = urlparse(url)
        host = parsed.hostname
    except ValueError:
        parsed, host = urlparse(""), None
    print(f"Base de datos: {host}")

    if host:
        # Ni el usuario ni la longitud son secretos; la contraseña no se muestra.
        print(f"Usuario: {unquote(parsed.username or '')} "
              f"(contraseña de {len(unquote(parsed.password or ''))} caracteres)")

    for problem in problems:
        print(f"  AVISO: {problem}")

    if not host:
        print("La cadena no tiene el formato "
              "postgresql://usuario:contraseña@host:5432/postgres")
        return 2

    if not args.confirmar:
        print("Es una prueba con usuarios desechables que se borran al final.")
        print("Ejecuta de nuevo con --confirmar para continuar.")
        return 2

    # Secreto efímero solo para firmar los tokens de esta ejecución.
    os.environ.setdefault(
        "FITNESS_TRACKER_JWT_SECRET", secrets.token_urlsafe(48)
    )

    from fastapi.testclient import TestClient

    from app.db import close_pool, get_connection
    from app.main import app
    from app.security import hash_password

    # Sin `with`: no se ejecuta el arranque (migraciones) de la aplicación.
    client = TestClient(app)
    password = secrets.token_urlsafe(24)
    suffix = secrets.token_hex(4)
    emails = {
        "A": f"a-{suffix}@{TEST_DOMAIN}",
        "B": f"b-{suffix}@{TEST_DOMAIN}",
    }
    user_ids: dict[str, int] = {}
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"  [{'OK' if ok else 'FALLO'}] {name} {detail}".rstrip())

    def login(email: str) -> dict[str, str]:
        response = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        response.raise_for_status()
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def export(headers) -> dict:
        response = client.get("/exports/fitness-tracker.json", headers=headers)
        response.raise_for_status()
        return response.json()

    def restore(headers, content: bytes, pwd: str, name="export.json"):
        return client.post(
            "/restores/account",
            headers=headers,
            files={"file": (name, BytesIO(content), "application/json")},
            data={"password": pwd},
        )

    try:
        print("1. Creando usuarios de prueba…")
        hashed = hash_password(password)

        with get_connection() as connection:
            for label, email in emails.items():
                user_ids[label] = seed_user(connection, email, label, hashed)

        headers_a, headers_b = login(emails["A"]), login(emails["B"])
        original_a, original_b = export(headers_a), export(headers_b)
        check("la exportación de A incluye datos de todas las secciones",
              bool(original_a.get("planned_workouts"))
              and bool(original_a.get("meal_templates")))

        print("2. Borrando los datos de A y restaurando…")
        with get_connection() as connection:
            for table in ROOT_TABLES:
                connection.execute(
                    f"DELETE FROM {table} WHERE user_id = ?", (user_ids["A"],)
                )

        started = time.perf_counter()
        response = restore(headers_a, json.dumps(original_a).encode(), password)
        elapsed = time.perf_counter() - started
        check("la restauración responde 200", response.status_code == 200,
              f"({elapsed:.1f} s)" if response.status_code == 200
              else f"→ {response.status_code} {response.text[:200]}")

        restored_a = export(headers_a)
        check("A queda idéntica a su exportación (salvo ids)",
              strip_ids(restored_a) == strip_ids(original_a))
        planned = restored_a["planned_workouts"][0]
        check("las relaciones apuntan a los ids nuevos",
              planned["workout_template_id"] == restored_a["workout_templates"][0]["id"]
              and planned["workout_session_id"] == restored_a["workout_sessions"][0]["id"])
        check("B no ha cambiado",
              strip_ids(export(headers_b)) == strip_ids(original_b))

        print("3. Casos que no deben cambiar nada…")
        wrong = restore(headers_a, json.dumps(original_a).encode(), "incorrecta")
        check("contraseña incorrecta rechazada",
              wrong.status_code in (400, 401, 403), f"→ {wrong.status_code}")
        invalid = restore(headers_a, b"esto no es json", password)
        check("archivo inválido rechazado (400)", invalid.status_code == 400,
              f"→ {invalid.status_code}")
        check("A sigue igual tras los rechazos",
              strip_ids(export(headers_a)) == strip_ids(original_a))
    except Exception as error:  # noqa: BLE001
        check("la prueba termina sin errores inesperados", False,
              f"→ {type(error).__name__}: {str(error)[:200]}")
    finally:
        print("4. Limpiando usuarios de prueba…")
        remaining = -1

        try:
            with get_connection() as connection:
                connection.execute(
                    "DELETE FROM users WHERE email LIKE ?",
                    (f"%-{suffix}@{TEST_DOMAIN}",),
                )
                remaining = connection.execute(
                    "SELECT COUNT(*) AS total FROM users WHERE email LIKE ?",
                    (f"%-{suffix}@{TEST_DOMAIN}",),
                ).fetchone()["total"]
        except Exception as error:  # noqa: BLE001
            print(f"  No se pudo limpiar: {type(error).__name__}")

        check("usuarios de prueba borrados", remaining == 0)
        close_pool()

    failed = [name for name, ok, _ in results if not ok]
    print()
    print("RESULTADO:", "TODO CORRECTO" if not failed else f"{len(failed)} fallo(s)")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
