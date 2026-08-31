import sqlite3


from fastapi import APIRouter, HTTPException, Response, status


from app.db import get_connection
from app.schemas import (
    NutritionFoodCreate,
    NutritionFoodResponse,
    NutritionFoodUpdate,
)


router = APIRouter(
    tags=["nutrition foods"],
)


def row_to_nutrition_food(row: sqlite3.Row) -> NutritionFoodResponse:
    return NutritionFoodResponse(
        id=row["id"],
        nutrition_meal_id=row["nutrition_meal_id"],
        name=row["name"],
        quantity_g=row["quantity_g"],
        calories=row["calories"],
        protein_g=row["protein_g"],
        carbs_g=row["carbs_g"],
        fat_g=row["fat_g"],
        position=row["position"],
        notes=row["notes"],
    )


def ensure_nutrition_meal_exists(meal_id: int) -> None:
    with get_connection() as connection:
        nutrition_meal = connection.execute(
            """
            SELECT id
            FROM nutrition_meals
            WHERE id = ?
            """,
            (meal_id,),
        ).fetchone()

    if nutrition_meal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una comida con ese id.",
        )


@router.post(
    "/nutrition-meals/{meal_id}/foods/",
    response_model=NutritionFoodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_food(
    meal_id: int,
    nutrition_food: NutritionFoodCreate,
) -> NutritionFoodResponse:
    ensure_nutrition_meal_exists(meal_id)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO nutrition_foods (
                    nutrition_meal_id,
                    name,
                    quantity_g,
                    calories,
                    protein_g,
                    carbs_g,
                    fat_g,
                    position,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_id,
                    nutrition_food.name.strip(),
                    nutrition_food.quantity_g,
                    nutrition_food.calories,
                    nutrition_food.protein_g,
                    nutrition_food.carbs_g,
                    nutrition_food.fat_g,
                    nutrition_food.position,
                    nutrition_food.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    nutrition_meal_id,
                    name,
                    quantity_g,
                    calories,
                    protein_g,
                    carbs_g,
                    fat_g,
                    position,
                    notes
                FROM nutrition_foods
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un alimento en esa posición para esta comida.",
        ) from error

    return row_to_nutrition_food(row)


@router.get(
    "/nutrition-meals/{meal_id}/foods/",
    response_model=list[NutritionFoodResponse],
)
def list_nutrition_foods(
    meal_id: int,
) -> list[NutritionFoodResponse]:
    ensure_nutrition_meal_exists(meal_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                nutrition_meal_id,
                name,
                quantity_g,
                calories,
                protein_g,
                carbs_g,
                fat_g,
                position,
                notes
            FROM nutrition_foods
            WHERE nutrition_meal_id = ?
            ORDER BY position ASC
            """,
            (meal_id,),
        ).fetchall()

    return [row_to_nutrition_food(row) for row in rows]


@router.get(
    "/nutrition-foods/{food_id}",
    response_model=NutritionFoodResponse,
)
def get_nutrition_food(food_id: int) -> NutritionFoodResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                nutrition_meal_id,
                name,
                quantity_g,
                calories,
                protein_g,
                carbs_g,
                fat_g,
                position,
                notes
            FROM nutrition_foods
            WHERE id = ?
            """,
            (food_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un alimento con ese id.",
        )

    return row_to_nutrition_food(row)


@router.put(
    "/nutrition-foods/{food_id}",
    response_model=NutritionFoodResponse,
)
def update_nutrition_food(
    food_id: int,
    nutrition_food: NutritionFoodUpdate,
) -> NutritionFoodResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE nutrition_foods
                SET
                    name = ?,
                    quantity_g = ?,
                    calories = ?,
                    protein_g = ?,
                    carbs_g = ?,
                    fat_g = ?,
                    position = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    nutrition_food.name.strip(),
                    nutrition_food.quantity_g,
                    nutrition_food.calories,
                    nutrition_food.protein_g,
                    nutrition_food.carbs_g,
                    nutrition_food.fat_g,
                    nutrition_food.position,
                    nutrition_food.notes,
                    food_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe un alimento con ese id.",
                )

            row = connection.execute(
                """
                SELECT
                    id,
                    nutrition_meal_id,
                    name,
                    quantity_g,
                    calories,
                    protein_g,
                    carbs_g,
                    fat_g,
                    position,
                    notes
                FROM nutrition_foods
                WHERE id = ?
                """,
                (food_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un alimento en esa posición para esta comida.",
            ) from error

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No se pudo actualizar el alimento: {error}",
        ) from error

    return row_to_nutrition_food(row)


@router.delete(
    "/nutrition-foods/{food_id}",
    response_model=None,
)
def delete_nutrition_food(food_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM nutrition_foods
            WHERE id = ?
            """,
            (food_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un alimento con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)