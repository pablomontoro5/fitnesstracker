from app.db import DATABASE_PATH, get_connection, initialize_database


def test_initialize_database_creates_daily_logs_table():
    initialize_database()

    with get_connection() as connection:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'daily_logs'
            """
        ).fetchone()

    assert table is not None


def test_daily_logs_has_expected_columns():
    initialize_database()

    with get_connection() as connection:
        columns = connection.execute(
            "PRAGMA table_info(daily_logs)"
        ).fetchall()

    column_names = {column["name"] for column in columns}

    assert column_names == {
        "id",
        "date",
        "steps",
        "notes",
        "created_at",
    }


def test_database_file_is_created():
    initialize_database()

    assert DATABASE_PATH.exists()