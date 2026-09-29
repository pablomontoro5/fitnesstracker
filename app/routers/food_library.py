import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    FoodLibraryCreate,
    FoodLibraryResponse,
    FoodLibraryUpdate,
    UserResponse,
)

router = APIRouter(prefix="/food-library", tags=["food library"])


def row_to_food(row: sqlite3.Row) -> FoodLibraryResponse:
    return FoodLibraryResponse(
        id=row["id"],
        name=row["name"],
        calories_per_100g=row["calories_per_100g"],
        protein_per_100g=row["protein_per_100g"],
        carbs_per_100g=row["carbs_per_100g"],
        fat_per_100g=row["fat_per_100g"],
        notes=row["notes"],
    )


def normalized_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre del alimento no puede estar vacío.",
        )
    return name


@router.post(
    "/",
    response_model=FoodLibraryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_food_library_item(
    food: FoodLibraryCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> FoodLibraryResponse:
    name = normalized_name(food.name)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO food_library (
                user_id, name, calories_per_100g, protein_per_100g,
                carbs_per_100g, fat_per_100g, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                name,
                food.calories_per_100g,
                food.protein_per_100g,
                food.carbs_per_100g,
                food.fat_per_100g,
                food.notes,
            ),
        )
        row = connection.execute(
            """
            SELECT id, name, calories_per_100g, protein_per_100g,
                   carbs_per_100g, fat_per_100g, notes
            FROM food_library
            WHERE id = ? AND user_id = ?
            """,
            (cursor.lastrowid, current_user.id),
        ).fetchone()
    return row_to_food(row)


@router.get("/", response_model=list[FoodLibraryResponse])
def list_food_library_items(
    current_user: UserResponse = Depends(get_current_user),
) -> list[FoodLibraryResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, calories_per_100g, protein_per_100g,
                   carbs_per_100g, fat_per_100g, notes
            FROM food_library
            WHERE user_id = ?
            ORDER BY name COLLATE NOCASE ASC, id ASC
            """,
            (current_user.id,),
        ).fetchall()
    return [row_to_food(row) for row in rows]


@router.get("/{food_id}", response_model=FoodLibraryResponse)
def get_food_library_item(
    food_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> FoodLibraryResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, calories_per_100g, protein_per_100g,
                   carbs_per_100g, fat_per_100g, notes
            FROM food_library
            WHERE id = ? AND user_id = ?
            """,
            (food_id, current_user.id),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un alimento en tu biblioteca con ese id.",
        )
    return row_to_food(row)


@router.put("/{food_id}", response_model=FoodLibraryResponse)
def update_food_library_item(
    food_id: int,
    food: FoodLibraryUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> FoodLibraryResponse:
    name = normalized_name(food.name)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE food_library
            SET name = ?, calories_per_100g = ?, protein_per_100g = ?,
                carbs_per_100g = ?, fat_per_100g = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                name,
                food.calories_per_100g,
                food.protein_per_100g,
                food.carbs_per_100g,
                food.fat_per_100g,
                food.notes,
                food_id,
                current_user.id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un alimento en tu biblioteca con ese id.",
            )
        row = connection.execute(
            """
            SELECT id, name, calories_per_100g, protein_per_100g,
                   carbs_per_100g, fat_per_100g, notes
            FROM food_library
            WHERE id = ? AND user_id = ?
            """,
            (food_id, current_user.id),
        ).fetchone()
    return row_to_food(row)


@router.delete(
    "/{food_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_food_library_item(
    food_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM food_library
            WHERE id = ? AND user_id = ?
            """,
            (food_id, current_user.id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un alimento en tu biblioteca con ese id.",
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)