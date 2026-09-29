import sqlite3

import pytest

from app.db import migrate_nutrition_days_table


@pytest.fixture
def legacy_connection(tmp_path):
    connection = sqlite3.connect(tmp_path / "legacy_nutrition.db")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE
        );
        CREATE TABLE nutrition_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE nutrition_meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nutrition_day_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nutrition_day_id)
                REFERENCES nutrition_days(id) ON DELETE CASCADE,
            UNIQUE (nutrition_day_id, position)
        );
        CREATE TABLE nutrition_foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nutrition_meal_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity_g REAL NOT NULL,
            calories REAL NOT NULL,
            protein_g REAL NOT NULL,
            carbs_g REAL NOT NULL,
            fat_g REAL NOT NULL,
            position INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nutrition_meal_id)
                REFERENCES nutrition_meals(id) ON DELETE CASCADE,
            UNIQUE (nutrition_meal_id, position)
        );
        """
    )
    try:
        yield connection
    finally:
        connection.close()


def migrate_with_foreign_keys_temporarily_disabled(connection):
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 0
    try:
        with connection:
            migrate_nutrition_days_table(connection)
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            assert violations == [], violations
    finally:
        connection.execute("PRAGMA foreign_keys = ON")
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_legacy_nutrition_preserves_day_meal_and_food(legacy_connection):
    connection = legacy_connection
    connection.execute("INSERT INTO users (id, email) VALUES (7, 'owner@example.com')")
    connection.execute(
        """
        INSERT INTO nutrition_days (id, date, notes, created_at)
        VALUES (11, '2026-08-31', 'Día heredado', '2026-08-31 08:00:00')
        """
    )
    connection.execute(
        """
        INSERT INTO nutrition_meals
            (id, nutrition_day_id, name, position, created_at)
        VALUES (21, 11, 'Desayuno', 1, '2026-08-31 08:01:00')
        """
    )
    connection.execute(
        """
        INSERT INTO nutrition_foods
            (id, nutrition_meal_id, name, quantity_g, calories,
             protein_g, carbs_g, fat_g, position, notes, created_at)
        VALUES
            (31, 21, 'Avena', 80, 304, 10.4, 48.8, 5.6,
             1, 'Pesada en seco', '2026-08-31 08:02:00')
        """
    )
    connection.commit()

    migrate_with_foreign_keys_temporarily_disabled(connection)

    day = connection.execute(
        "SELECT * FROM nutrition_days WHERE id = 11"
    ).fetchone()
    meal = connection.execute(
        "SELECT * FROM nutrition_meals WHERE id = 21"
    ).fetchone()
    food = connection.execute(
        "SELECT * FROM nutrition_foods WHERE id = 31"
    ).fetchone()

    assert day is not None
    assert (day["user_id"], day["date"], day["notes"], day["created_at"]) == (
        7, "2026-08-31", "Día heredado", "2026-08-31 08:00:00"
    )
    assert meal is not None
    assert (meal["nutrition_day_id"], meal["name"], meal["position"]) == (
        11, "Desayuno", 1
    )
    assert food is not None
    assert (
        food["nutrition_meal_id"], food["name"], food["quantity_g"],
        food["calories"], food["protein_g"], food["carbs_g"],
        food["fat_g"], food["position"], food["notes"]
    ) == (21, "Avena", 80, 304, 10.4, 48.8, 5.6, 1, "Pesada en seco")
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    migrate_with_foreign_keys_temporarily_disabled(connection)
    assert connection.execute("SELECT COUNT(*) FROM nutrition_days").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM nutrition_meals").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM nutrition_foods").fetchone()[0] == 1

    connection.execute("INSERT INTO users (id, email) VALUES (8, 'second@example.com')")
    connection.execute(
        """
        INSERT INTO nutrition_days (user_id, date, notes)
        VALUES (8, '2026-08-31', 'Misma fecha, otro usuario')
        """
    )
    connection.commit()
    assert connection.execute(
        "SELECT COUNT(*) FROM nutrition_days WHERE date = '2026-08-31'"
    ).fetchone()[0] == 2
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_legacy_data_with_multiple_users_is_not_assigned_arbitrarily(
    legacy_connection,
):
    connection = legacy_connection
    connection.execute("INSERT INTO users (id, email) VALUES (1, 'a@example.com')")
    connection.execute("INSERT INTO users (id, email) VALUES (2, 'b@example.com')")
    connection.execute(
        "INSERT INTO nutrition_days (id, date) VALUES (11, '2026-08-31')"
    )
    connection.commit()

    with pytest.raises(RuntimeError):
        migrate_with_foreign_keys_temporarily_disabled(connection)

    assert connection.execute(
        "SELECT id, date FROM nutrition_days WHERE id = 11"
    ).fetchone()["date"] == "2026-08-31"
    assert "user_id" not in {
        column["name"]
        for column in connection.execute("PRAGMA table_info(nutrition_days)")
    }
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_empty_legacy_table_migrates_without_users(legacy_connection):
    connection = legacy_connection
    migrate_with_foreign_keys_temporarily_disabled(connection)
    columns = {
        column["name"]: column
        for column in connection.execute("PRAGMA table_info(nutrition_days)")
    }
    assert columns["user_id"]["notnull"] == 1
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []