import sqlite3


from fastapi import APIRouter, HTTPException, Response, status


from app.db import get_connection
from app.schemas import (
    NutritionMealCreate,
    NutritionMealResponse,
    NutritionMealUpdate,
)


router = APIRouter(
    tags=["nutrition meals"],
)


def row_to_nutrition_meal(row: sqlite3.Row) -> NutritionMealResponse:
    return NutritionMealResponse(
        id=row["id"],
        nutrition_day_id=row["nutrition_day_id"],
        name=row["name"],
        position=row["position"],
    )


def ensure_nutrition_day_exists(day_id: int) -> None:
    with get_connection() as connection:
        nutrition_day = connection.execute(
            """
            SELECT id
            FROM nutrition_days
            WHERE id = ?
            """,
            (day_id,),
        ).fetchone()

    if nutrition_day is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro nutricional con ese id.",
        )


@router.post(
    "/nutrition-days/{day_id}/meals/",
    response_model=NutritionMealResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_meal(
    day_id: int,
    nutrition_meal: NutritionMealCreate,
) -> NutritionMealResponse:
    ensure_nutrition_day_exists(day_id)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO nutrition_meals (
                    nutrition_day_id,
                    name,
                    position
                )
                VALUES (?, ?, ?)
                """,
                (
                    day_id,
                    nutrition_meal.name.strip(),
                    nutrition_meal.position,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    nutrition_day_id,
                    name,
                    position
                FROM nutrition_meals
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una comida en esa posición para este día.",
        ) from error

    return row_to_nutrition_meal(row)


@router.get(
    "/nutrition-days/{day_id}/meals/",
    response_model=list[NutritionMealResponse],
)
def list_nutrition_meals(
    day_id: int,
) -> list[NutritionMealResponse]:
    ensure_nutrition_day_exists(day_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                nutrition_day_id,
                name,
                position
            FROM nutrition_meals
            WHERE nutrition_day_id = ?
            ORDER BY position ASC
            """,
            (day_id,),
        ).fetchall()

    return [row_to_nutrition_meal(row) for row in rows]


@router.get(
    "/nutrition-meals/{meal_id}",
    response_model=NutritionMealResponse,
)
def get_nutrition_meal(meal_id: int) -> NutritionMealResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                nutrition_day_id,
                name,
                position
            FROM nutrition_meals
            WHERE id = ?
            """,
            (meal_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una comida con ese id.",
        )

    return row_to_nutrition_meal(row)


@router.put(
    "/nutrition-meals/{meal_id}",
    response_model=NutritionMealResponse,
)
def update_nutrition_meal(
    meal_id: int,
    nutrition_meal: NutritionMealUpdate,
) -> NutritionMealResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE nutrition_meals
                SET
                    name = ?,
                    position = ?
                WHERE id = ?
                """,
                (
                    nutrition_meal.name.strip(),
                    nutrition_meal.position,
                    meal_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe una comida con ese id.",
                )

            row = connection.execute(
                """
                SELECT
                    id,
                    nutrition_day_id,
                    name,
                    position
                FROM nutrition_meals
                WHERE id = ?
                """,
                (meal_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una comida en esa posición para este día.",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No se pudo actualizar la comida: {error}",
        ) from error

    return row_to_nutrition_meal(row)


@router.delete(
    "/nutrition-meals/{meal_id}",
    response_model=None,
)
def delete_nutrition_meal(meal_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM nutrition_meals
            WHERE id = ?
            """,
            (meal_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una comida con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)