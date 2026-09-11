from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.routers.goals import build_goals_progress


def test_create_or_update_daily_steps_goal():
    with TestClient(app) as client:
        response = client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )

        list_response = client.get("/goals/")

    assert response.status_code == 200

    goal = response.json()

    assert goal["goal_type"] == "daily_steps"
    assert goal["target_value"] == 8000

    assert list_response.status_code == 200
    assert list_response.json() == [goal]


def test_updating_goal_does_not_create_duplicate():
    with TestClient(app) as client:
        first_response = client.put(
            "/goals/weekly_workouts",
            json={
                "target_value": 3,
            },
        )

        second_response = client.put(
            "/goals/weekly_workouts",
            json={
                "target_value": 4,
            },
        )

        list_response = client.get("/goals/")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["id"] == first_response.json()["id"]
    assert second_response.json()["target_value"] == 4
    assert list_response.json() == [second_response.json()]


def test_delete_goal():
    with TestClient(app) as client:
        create_response = client.put(
            "/goals/weekly_running_km",
            json={
                "target_value": 12.5,
            },
        )

        assert create_response.status_code == 200

        delete_response = client.delete("/goals/weekly_running_km")
        list_response = client.get("/goals/")

    assert delete_response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_missing_goal_returns_not_found():
    with TestClient(app) as client:
        response = client.delete("/goals/daily_steps")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe un objetivo de este tipo."
    }


def test_goal_type_must_be_supported():
    with TestClient(app) as client:
        response = client.put(
            "/goals/monthly_steps",
            json={
                "target_value": 100000,
            },
        )

    assert response.status_code == 422


def test_goal_target_value_must_be_positive():
    with TestClient(app) as client:
        response = client.put(
            "/goals/daily_steps",
            json={
                "target_value": 0,
            },
        )

    assert response.status_code == 422


def test_goals_progress_calculates_today_and_current_week():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )
        client.put(
            "/goals/weekly_workouts",
            json={
                "target_value": 3,
            },
        )
        client.put(
            "/goals/weekly_running_km",
            json={
                "target_value": 10,
            },
        )

        client.post(
            "/daily-logs/",
            json={
                "date": "2026-09-09",
                "steps": 6400,
                "notes": None,
            },
        )

        client.post(
            "/workout-sessions/",
            json={
                "date": "2026-09-07",
                "name": "Empujes",
                "notes": None,
            },
        )
        client.post(
            "/workout-sessions/",
            json={
                "date": "2026-09-09",
                "name": "Tirón",
                "notes": None,
            },
        )
        client.post(
            "/workout-sessions/",
            json={
                "date": "2026-09-06",
                "name": "Sesión anterior",
                "notes": None,
            },
        )

        client.post(
            "/runs/",
            json={
                "date": "2026-09-07",
                "distance_km": 4.5,
                "duration_seconds": 1500,
                "notes": None,
            },
        )
        client.post(
            "/runs/",
            json={
                "date": "2026-09-09",
                "distance_km": 3.2,
                "duration_seconds": 1200,
                "notes": None,
            },
        )
        client.post(
            "/runs/",
            json={
                "date": "2026-09-06",
                "distance_km": 10,
                "duration_seconds": 3600,
                "notes": None,
            },
        )

    progress_by_type = {
        progress.goal_type: progress
        for progress in build_goals_progress(today=today)
    }

    steps_progress = progress_by_type["daily_steps"]
    workouts_progress = progress_by_type["weekly_workouts"]
    running_progress = progress_by_type["weekly_running_km"]

    assert steps_progress.current_value == 6400
    assert steps_progress.target_value == 8000
    assert steps_progress.progress_percentage == 80
    assert steps_progress.is_completed is False

    assert workouts_progress.current_value == 2
    assert workouts_progress.target_value == 3
    assert workouts_progress.progress_percentage == 66.7
    assert workouts_progress.is_completed is False

    assert running_progress.current_value == 7.7
    assert running_progress.target_value == 10
    assert running_progress.progress_percentage == 77
    assert running_progress.is_completed is False


def test_goals_progress_caps_percentage_at_one_hundred():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )
        client.post(
            "/daily-logs/",
            json={
                "date": "2026-09-09",
                "steps": 10000,
                "notes": None,
            },
        )

    progress_items = build_goals_progress(today=today)

    assert len(progress_items) == 1

    progress = progress_items[0]

    assert progress.goal_type == "daily_steps"
    assert progress.current_value == 10000
    assert progress.progress_percentage == 100
    assert progress.is_completed is True

def create_nutrition_day(
    client: TestClient,
    *,
    date_value: str,
) -> dict:
    response = client.post(
        "/nutrition-days/",
        json={
            "date": date_value,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_nutrition_meal(
    client: TestClient,
    *,
    day_id: int,
    name: str = "Comida",
    position: int = 1,
) -> dict:
    response = client.post(
        f"/nutrition-days/{day_id}/meals/",
        json={
            "name": name,
            "position": position,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_nutrition_food(
    client: TestClient,
    *,
    meal_id: int,
    name: str = "Alimento",
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    position: int = 1,
) -> dict:
    response = client.post(
        f"/nutrition-meals/{meal_id}/foods/",
        json={
            "name": name,
            "quantity_g": 100,
            "calories": calories,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "position": position,
            "notes": None,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_nutrition_goal():
    with TestClient(app) as client:
        response = client.put(
            "/goals/daily_protein_g",
            json={
                "target_value": 150,
            },
        )

    assert response.status_code == 200
    assert response.json()["goal_type"] == "daily_protein_g"
    assert response.json()["target_value"] == 150


def test_nutrition_goal_progress_returns_zero_without_day_or_goals():
    with TestClient(app) as client:
        response = client.get(
            "/goals/nutrition-progress",
            params={"target_date": "2026-09-11"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-09-11",
        "calories": {
            "current_value": 0,
            "target_value": None,
            "remaining_value": None,
            "progress_percentage": None,
            "is_completed": False,
        },
        "protein_g": {
            "current_value": 0,
            "target_value": None,
            "remaining_value": None,
            "progress_percentage": None,
            "is_completed": False,
        },
        "carbs_g": {
            "current_value": 0,
            "target_value": None,
            "remaining_value": None,
            "progress_percentage": None,
            "is_completed": False,
        },
        "fat_g": {
            "current_value": 0,
            "target_value": None,
            "remaining_value": None,
            "progress_percentage": None,
            "is_completed": False,
        },
    }


def test_nutrition_goal_progress_aggregates_foods_and_goals():
    target_date = "2026-09-11"

    with TestClient(app) as client:
        client.put(
            "/goals/daily_calories",
            json={"target_value": 2000},
        )
        client.put(
            "/goals/daily_protein_g",
            json={"target_value": 150},
        )
        client.put(
            "/goals/daily_carbs_g",
            json={"target_value": 250},
        )
        client.put(
            "/goals/daily_fat_g",
            json={"target_value": 70},
        )

        nutrition_day = create_nutrition_day(
            client,
            date_value=target_date,
        )
        breakfast = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
            name="Desayuno",
            position=1,
        )
        dinner = create_nutrition_meal(
            client,
            day_id=nutrition_day["id"],
            name="Cena",
            position=2,
        )

        create_nutrition_food(
            client,
            meal_id=breakfast["id"],
            name="Avena",
            calories=400,
            protein_g=15,
            carbs_g=65,
            fat_g=8,
            position=1,
        )
        create_nutrition_food(
            client,
            meal_id=dinner["id"],
            name="Pollo con arroz",
            calories=1900,
            protein_g=145,
            carbs_g=200,
            fat_g=65,
            position=1,
        )

        response = client.get(
            "/goals/nutrition-progress",
            params={"target_date": target_date},
        )

    assert response.status_code == 200

    body = response.json()

    assert body["calories"] == {
        "current_value": 2300,
        "target_value": 2000,
        "remaining_value": -300,
        "progress_percentage": 115,
        "is_completed": True,
    }
    assert body["protein_g"] == {
        "current_value": 160,
        "target_value": 150,
        "remaining_value": -10,
        "progress_percentage": 106.7,
        "is_completed": True,
    }
    assert body["carbs_g"] == {
        "current_value": 265,
        "target_value": 250,
        "remaining_value": -15,
        "progress_percentage": 106,
        "is_completed": True,
    }
    assert body["fat_g"] == {
        "current_value": 73,
        "target_value": 70,
        "remaining_value": -3,
        "progress_percentage": 104.3,
        "is_completed": True,
    }


def test_nutrition_goal_progress_only_uses_requested_date():
    with TestClient(app) as client:
        client.put(
            "/goals/daily_calories",
            json={"target_value": 2000},
        )

        selected_day = create_nutrition_day(
            client,
            date_value="2026-09-11",
        )
        selected_meal = create_nutrition_meal(
            client,
            day_id=selected_day["id"],
        )
        create_nutrition_food(
            client,
            meal_id=selected_meal["id"],
            calories=500,
            protein_g=20,
            carbs_g=50,
            fat_g=10,
        )

        other_day = create_nutrition_day(
            client,
            date_value="2026-09-12",
        )
        other_meal = create_nutrition_meal(
            client,
            day_id=other_day["id"],
        )
        create_nutrition_food(
            client,
            meal_id=other_meal["id"],
            calories=1500,
            protein_g=70,
            carbs_g=150,
            fat_g=50,
        )

        response = client.get(
            "/goals/nutrition-progress",
            params={"target_date": "2026-09-11"},
        )

    assert response.status_code == 200
    assert response.json()["calories"]["current_value"] == 500
    assert response.json()["calories"]["remaining_value"] == 1500
    assert response.json()["calories"]["progress_percentage"] == 25
    assert response.json()["calories"]["is_completed"] is False


def test_nutrition_goal_progress_rejects_invalid_date():
    with TestClient(app) as client:
        response = client.get(
            "/goals/nutrition-progress",
            params={"target_date": "invalid-date"},
        )

    assert response.status_code == 422

def create_recovery_log(
    client: TestClient,
    *,
    log_date: str,
    sleep_minutes: int | None = None,
    sleep_quality: int | None = None,
    is_rest_day: bool = False,
    notes: str | None = None,
) -> dict:
    response = client.post(
        "/recovery-logs/",
        json={
            "date": log_date,
            "sleep_minutes": sleep_minutes,
            "sleep_quality": sleep_quality,
            "is_rest_day": is_rest_day,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_goals_progress_includes_sleep_and_rest_day_goals():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/daily_sleep_minutes",
            json={
                "target_value": 480,
            },
        )
        client.put(
            "/goals/weekly_rest_days",
            json={
                "target_value": 3,
            },
        )

        create_recovery_log(
            client,
            log_date="2026-09-09",
            sleep_minutes=450,
            sleep_quality=4,
            is_rest_day=False,
        )
        create_recovery_log(
            client,
            log_date="2026-09-08",
            sleep_minutes=490,
            sleep_quality=5,
            is_rest_day=True,
        )
        create_recovery_log(
            client,
            log_date="2026-09-07",
            sleep_minutes=470,
            sleep_quality=3,
            is_rest_day=True,
        )
        create_recovery_log(
            client,
            log_date="2026-09-06",
            sleep_minutes=510,
            sleep_quality=4,
            is_rest_day=True,
        )

    progress_by_type = {
        progress.goal_type: progress
        for progress in build_goals_progress(today=today)
    }

    sleep_progress = progress_by_type["daily_sleep_minutes"]
    rest_days_progress = progress_by_type["weekly_rest_days"]

    assert sleep_progress.current_value == 450
    assert sleep_progress.target_value == 480
    assert sleep_progress.progress_percentage == 93.8
    assert sleep_progress.is_completed is False

    assert rest_days_progress.current_value == 2
    assert rest_days_progress.target_value == 3
    assert rest_days_progress.progress_percentage == 66.7
    assert rest_days_progress.is_completed is False


def test_weekly_rest_days_excludes_logs_before_current_week():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/weekly_rest_days",
            json={
                "target_value": 2,
            },
        )

        create_recovery_log(
            client,
            log_date="2026-09-07",
            is_rest_day=True,
        )
        create_recovery_log(
            client,
            log_date="2026-09-06",
            is_rest_day=True,
        )

    progress_items = build_goals_progress(today=today)
    progress_by_type = {
        progress.goal_type: progress
        for progress in progress_items
    }

    rest_days_progress = progress_by_type["weekly_rest_days"]

    assert rest_days_progress.current_value == 1
    assert rest_days_progress.target_value == 2
    assert rest_days_progress.progress_percentage == 50
    assert rest_days_progress.is_completed is False


def test_goals_progress_excludes_nutrition_goal_types():
    today = date(2026, 9, 9)

    with TestClient(app) as client:
        client.put(
            "/goals/daily_steps",
            json={
                "target_value": 8000,
            },
        )
        client.put(
            "/goals/daily_calories",
            json={
                "target_value": 2400,
            },
        )
        client.put(
            "/goals/daily_protein_g",
            json={
                "target_value": 150,
            },
        )

    progress_goal_types = {
        progress.goal_type
        for progress in build_goals_progress(today=today)
    }

    assert progress_goal_types == {"daily_steps"}