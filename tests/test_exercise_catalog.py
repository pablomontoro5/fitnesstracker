from fastapi.testclient import TestClient

from app.main import app


def test_list_exercise_catalog():
    with TestClient(app) as client:
        response = client.get("/exercise-catalog/")

    assert response.status_code == 200

    exercises = response.json()

    assert len(exercises) >= 20

    bench_press = next(
        exercise
        for exercise in exercises
        if exercise["id"] == "barbell-bench-press"
    )

    assert bench_press == {
        "id": "barbell-bench-press",
        "name": "Press banca con barra",
        "slug": "barbell-bench-press",
        "primary_muscle_group": "Pectoral",
        "secondary_muscle_groups": [
            "Tríceps",
            "Deltoides anterior",
        ],
        "equipment": "barbell",
        "movement_pattern": "horizontal_push",
        "exercise_type": "compound",
        "variants": [
            "Agarre medio",
            "Agarre cerrado",
            "Con pausa",
        ],
        "instructions": [
            "Apoya firmemente pies, glúteos y parte alta de la espalda.",
            "Mantén los omóplatos retraídos y deprimidos.",
            "Baja la barra con control y empuja manteniendo las muñecas alineadas.",
        ],
        "default_rep_range": "5-12",
    }


def test_exercise_catalog_filters_by_equipment_and_movement_pattern():
    with TestClient(app) as client:
        response = client.get(
            "/exercise-catalog/",
            params={
                "equipment": "barbell",
                "movement_pattern": "horizontal_push",
            },
        )

    assert response.status_code == 200
    assert [
        exercise["id"]
        for exercise in response.json()
    ] == ["barbell-bench-press"]


def test_exercise_catalog_filters_by_primary_muscle_group_case_insensitively():
    with TestClient(app) as client:
        response = client.get(
            "/exercise-catalog/",
            params={
                "primary_muscle_group": "pectorAL",
            },
        )

    assert response.status_code == 200
    assert {
        exercise["id"]
        for exercise in response.json()
    } == {
        "barbell-bench-press",
        "dumbbell-incline-bench-press",
        "parallel-bar-dip",
    }


def test_exercise_catalog_searches_name_variants_and_secondary_muscles():
    with TestClient(app) as client:
        name_response = client.get(
            "/exercise-catalog/",
            params={"search": "prensa"},
        )
        variant_response = client.get(
            "/exercise-catalog/",
            params={"search": "sumo"},
        )
        secondary_muscle_response = client.get(
            "/exercise-catalog/",
            params={"search": "antebrazos"},
        )

    assert name_response.status_code == 200
    assert "leg-press" in {
        exercise["id"]
        for exercise in name_response.json()
    }

    assert variant_response.status_code == 200
    assert {
        exercise["id"]
        for exercise in variant_response.json()
    } == {"barbell-deadlift"}

    assert secondary_muscle_response.status_code == 200
    assert {
        exercise["id"]
        for exercise in secondary_muscle_response.json()
    } == {
        "barbell-romanian-deadlift",
        "barbell-biceps-curl",
        "cable-triceps-pushdown",
    }


def test_get_exercise_catalog_item():
    with TestClient(app) as client:
        response = client.get(
            "/exercise-catalog/dumbbell-lateral-raise",
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Elevación lateral con mancuernas"
    assert response.json()["primary_muscle_group"] == "Deltoides lateral"
    assert response.json()["equipment"] == "dumbbell"


def test_get_missing_exercise_catalog_item_returns_not_found():
    with TestClient(app) as client:
        response = client.get("/exercise-catalog/missing-exercise")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No existe un ejercicio con ese id."
    }


def test_exercise_catalog_rejects_invalid_filter_value():
    with TestClient(app) as client:
        response = client.get(
            "/exercise-catalog/",
            params={"equipment": "invalid-equipment"},
        )

    assert response.status_code == 422