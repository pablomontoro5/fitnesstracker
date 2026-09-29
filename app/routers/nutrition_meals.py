import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    NutritionMealCreate,
    NutritionMealResponse,
    NutritionMealUpdate,
    UserResponse,
)


router = APIRouter(tags=["nutrition meals"])


def row_to_nutrition_meal(row: sqlite3.Row) -> NutritionMealResponse:
    return NutritionMealResponse(
        id=row["id"],
        nutrition_day_id=row["nutrition_day_id"],
        name=row["name"],
        position=row["position"],
    )


def ensure_owned_nutrition_day(
    connection: sqlite3.Connection,
    day_id: int,
    user_id: int,
) -> None:
    row = connection.execute(
        """
        SELECT id
        FROM nutrition_days
        WHERE id = ? AND user_id = ?
        """,
        (day_id, user_id),
    ).fetchone()
    if row is None:
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
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionMealResponse:
    name = nutrition_meal.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre de la comida no puede estar vacío.",
        )

    try:
        with get_connection() as connection:
            ensure_owned_nutrition_day(connection, day_id, current_user.id)
            cursor = connection.execute(
                """
                INSERT INTO nutrition_meals (nutrition_day_id, name, position)
                VALUES (?, ?, ?)
                """,
                (day_id, name, nutrition_meal.position),
            )
            row = connection.execute(
                """
                SELECT id, nutrition_day_id, name, position
                FROM nutrition_meals
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" not in str(error):
            raise
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
    current_user: UserResponse = Depends(get_current_user),
) -> list[NutritionMealResponse]:
    with get_connection() as connection:
        ensure_owned_nutrition_day(connection, day_id, current_user.id)
        rows = connection.execute(
            """
            SELECT id, nutrition_day_id, name, position
            FROM nutrition_meals
            WHERE nutrition_day_id = ?
            ORDER BY position ASC, id ASC
            """,
            (day_id,),
        ).fetchall()

    return [row_to_nutrition_meal(row) for row in rows]


@router.get(
    "/nutrition-meals/{meal_id}",
    response_model=NutritionMealResponse,
)
def get_nutrition_meal(
    meal_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionMealResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT m.id, m.nutrition_day_id, m.name, m.position
            FROM nutrition_meals AS m
            JOIN nutrition_days AS d ON d.id = m.nutrition_day_id
            WHERE m.id = ? AND d.user_id = ?
            """,
            (meal_id, current_user.id),
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
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionMealResponse:
    name = nutrition_meal.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre de la comida no puede estar vacío.",
        )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE nutrition_meals
                SET name = ?, position = ?
                WHERE id = ?
                  AND nutrition_day_id IN (
                      SELECT id FROM nutrition_days WHERE user_id = ?
                  )
                """,
                (name, nutrition_meal.position, meal_id, current_user.id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe una comida con ese id.",
                )
            row = connection.execute(
                """
                SELECT id, nutrition_day_id, name, position
                FROM nutrition_meals
                WHERE id = ?
                """,
                (meal_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" not in str(error):
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una comida en esa posición para este día.",
        ) from error

    return row_to_nutrition_meal(row)


@router.delete(
    "/nutrition-meals/{meal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_nutrition_meal(
    meal_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM nutrition_meals
            WHERE id = ?
              AND nutrition_day_id IN (
                  SELECT id FROM nutrition_days WHERE user_id = ?
              )
            """,
            (meal_id, current_user.id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una comida con ese id.",
            )

    return Response(status_code=status.HTTP_204_NO_CONTENT)