
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import Connection, IntegrityError, get_connection, is_unique_violation as _is_unique_violation
from app.dependencies import get_current_user
from app.schemas import (
    NutritionFoodCreate,
    NutritionFoodResponse,
    NutritionFoodUpdate,
    UserResponse,
)


router = APIRouter(tags=["nutrition foods"])


FOOD_COLUMNS = """
    id, nutrition_meal_id, name, quantity_g, calories,
    protein_g, carbs_g, fat_g, position, notes
"""


def row_to_nutrition_food(row: dict) -> NutritionFoodResponse:
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


def ensure_owned_nutrition_meal(
    connection: Connection,
    meal_id: int,
    user_id: int,
) -> None:
    row = connection.execute(
        """
        SELECT m.id
        FROM nutrition_meals AS m
        JOIN nutrition_days AS d ON d.id = m.nutrition_day_id
        WHERE m.id = ? AND d.user_id = ?
        """,
        (meal_id, user_id),
    ).fetchone()
    if row is None:
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
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionFoodResponse:
    name = nutrition_food.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre del alimento no puede estar vacío.",
        )

    try:
        with get_connection() as connection:
            ensure_owned_nutrition_meal(connection, meal_id, current_user.id)
            cursor = connection.execute(
                """
                INSERT INTO nutrition_foods (
                    nutrition_meal_id, name, quantity_g, calories,
                    protein_g, carbs_g, fat_g, position, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_id,
                    name,
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
                f"SELECT {FOOD_COLUMNS} FROM nutrition_foods WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
    except IntegrityError as error:
        if not _is_unique_violation(error):
            raise
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
    current_user: UserResponse = Depends(get_current_user),
) -> list[NutritionFoodResponse]:
    with get_connection() as connection:
        ensure_owned_nutrition_meal(connection, meal_id, current_user.id)
        rows = connection.execute(
            f"""
            SELECT {FOOD_COLUMNS}
            FROM nutrition_foods
            WHERE nutrition_meal_id = ?
            ORDER BY position ASC, id ASC
            """,
            (meal_id,),
        ).fetchall()

    return [row_to_nutrition_food(row) for row in rows]


@router.get(
    "/nutrition-foods/{food_id}",
    response_model=NutritionFoodResponse,
)
def get_nutrition_food(
    food_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionFoodResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT f.id, f.nutrition_meal_id, f.name, f.quantity_g,
                   f.calories, f.protein_g, f.carbs_g, f.fat_g,
                   f.position, f.notes
            FROM nutrition_foods AS f
            JOIN nutrition_meals AS m ON m.id = f.nutrition_meal_id
            JOIN nutrition_days AS d ON d.id = m.nutrition_day_id
            WHERE f.id = ? AND d.user_id = ?
            """,
            (food_id, current_user.id),
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
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionFoodResponse:
    name = nutrition_food.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre del alimento no puede estar vacío.",
        )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE nutrition_foods
                SET name = ?, quantity_g = ?, calories = ?,
                    protein_g = ?, carbs_g = ?, fat_g = ?,
                    position = ?, notes = ?
                WHERE id = ?
                  AND nutrition_meal_id IN (
                      SELECT m.id
                      FROM nutrition_meals AS m
                      JOIN nutrition_days AS d ON d.id = m.nutrition_day_id
                      WHERE d.user_id = ?
                  )
                """,
                (
                    name,
                    nutrition_food.quantity_g,
                    nutrition_food.calories,
                    nutrition_food.protein_g,
                    nutrition_food.carbs_g,
                    nutrition_food.fat_g,
                    nutrition_food.position,
                    nutrition_food.notes,
                    food_id,
                    current_user.id,
                ),
            )
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe un alimento con ese id.",
                )
            row = connection.execute(
                f"SELECT {FOOD_COLUMNS} FROM nutrition_foods WHERE id = ?",
                (food_id,),
            ).fetchone()
    except IntegrityError as error:
        if not _is_unique_violation(error):
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un alimento en esa posición para esta comida.",
        ) from error

    return row_to_nutrition_food(row)


@router.delete(
    "/nutrition-foods/{food_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_nutrition_food(
    food_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM nutrition_foods
            WHERE id = ?
              AND nutrition_meal_id IN (
                  SELECT m.id
                  FROM nutrition_meals AS m
                  JOIN nutrition_days AS d ON d.id = m.nutrition_day_id
                  WHERE d.user_id = ?
              )
            """,
            (food_id, current_user.id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un alimento con ese id.",
            )

    return Response(status_code=status.HTTP_204_NO_CONTENT)