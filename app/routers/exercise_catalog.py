from fastapi import APIRouter, HTTPException, Query, status

from app.exercise_catalog import EXERCISE_CATALOG
from app.schemas import (
    EquipmentType,
    ExerciseCatalogItemResponse,
    ExerciseType,
    MovementPattern,
)


router = APIRouter(
    prefix="/exercise-catalog",
    tags=["exercise catalog"],
)


def matches_search(
    exercise: dict,
    search: str,
) -> bool:
    normalized_search = search.casefold()

    searchable_values = [
        exercise["name"],
        exercise["primary_muscle_group"],
        exercise["equipment"],
        exercise["movement_pattern"],
        exercise["exercise_type"],
        *exercise["secondary_muscle_groups"],
        *exercise["variants"],
    ]

    return any(
        normalized_search in value.casefold()
        for value in searchable_values
    )


@router.get(
    "/",
    response_model=list[ExerciseCatalogItemResponse],
)
def list_exercise_catalog(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
    ),
    primary_muscle_group: str | None = Query(
        default=None,
        min_length=1,
        max_length=80,
    ),
    equipment: EquipmentType | None = None,
    movement_pattern: MovementPattern | None = None,
    exercise_type: ExerciseType | None = None,
) -> list[ExerciseCatalogItemResponse]:
    exercises = list(EXERCISE_CATALOG)

    if search is not None:
        exercises = [
            exercise
            for exercise in exercises
            if matches_search(exercise, search)
        ]

    if primary_muscle_group is not None:
        normalized_muscle_group = primary_muscle_group.casefold()

        exercises = [
            exercise
            for exercise in exercises
            if (
                exercise["primary_muscle_group"].casefold()
                == normalized_muscle_group
            )
        ]

    if equipment is not None:
        exercises = [
            exercise
            for exercise in exercises
            if exercise["equipment"] == equipment
        ]

    if movement_pattern is not None:
        exercises = [
            exercise
            for exercise in exercises
            if exercise["movement_pattern"] == movement_pattern
        ]

    if exercise_type is not None:
        exercises = [
            exercise
            for exercise in exercises
            if exercise["exercise_type"] == exercise_type
        ]

    return [
        ExerciseCatalogItemResponse(**exercise)
        for exercise in exercises
    ]


@router.get(
    "/{exercise_id}",
    response_model=ExerciseCatalogItemResponse,
)
def get_exercise_catalog_item(
    exercise_id: str,
) -> ExerciseCatalogItemResponse:
    exercise = next(
        (
            catalog_item
            for catalog_item in EXERCISE_CATALOG
            if catalog_item["id"] == exercise_id
        ),
        None,
    )

    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio con ese id.",
        )

    return ExerciseCatalogItemResponse(**exercise)