import pytest

from app.db import get_connection, initialize_database


@pytest.fixture(autouse=True)
def clean_database():
    initialize_database()

    with get_connection() as connection:
        connection.execute("DELETE FROM workout_sets")
        connection.execute("DELETE FROM workout_exercises")
        connection.execute("DELETE FROM workout_sessions")
        connection.execute("DELETE FROM body_metrics")
        connection.execute("DELETE FROM daily_logs")

    yield

    with get_connection() as connection:
        connection.execute("DELETE FROM workout_sets")
        connection.execute("DELETE FROM workout_exercises")
        connection.execute("DELETE FROM workout_sessions")
        connection.execute("DELETE FROM body_metrics")
        connection.execute("DELETE FROM daily_logs")