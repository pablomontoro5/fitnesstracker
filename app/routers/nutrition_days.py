from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import IntegrityError, get_connection
from app.dependencies import get_current_user
from app.schemas import (
    NutritionDayCreate,
    NutritionDayResponse,
    NutritionDayUpdate,
    UserResponse,
)


router = APIRouter(
    prefix="/nutrition-days",
    tags=["nutrition days"],
)


def row_to_nutrition_day(row: dict) -> NutritionDayResponse:
    return NutritionDayResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        notes=row["notes"],
    )


@router.post(
    "/",
    response_model=NutritionDayResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_day(
    nutrition_day: NutritionDayCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionDayResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO nutrition_days (user_id, date, notes)
                VALUES (?, ?, ?)
                """,
                (
                    current_user.id,
                    nutrition_day.date.isoformat(),
                    nutrition_day.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT id, date, notes
                FROM nutrition_days
                WHERE id = ? AND user_id = ?
                """,
                (cursor.lastrowid, current_user.id),
            ).fetchone()
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro nutricional para esta fecha.",
        ) from error

    return row_to_nutrition_day(row)


@router.get(
    "/",
    response_model=list[NutritionDayResponse],
)
def list_nutrition_days(
    current_user: UserResponse = Depends(get_current_user),
) -> list[NutritionDayResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, date, notes
            FROM nutrition_days
            WHERE user_id = ?
            ORDER BY date DESC
            """,
            (current_user.id,),
        ).fetchall()

    return [row_to_nutrition_day(row) for row in rows]


@router.get(
    "/{day_date}",
    response_model=NutritionDayResponse,
)
def get_nutrition_day(
    day_date: date,
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionDayResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, date, notes
            FROM nutrition_days
            WHERE date = ? AND user_id = ?
            """,
            (day_date.isoformat(), current_user.id),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro nutricional para esta fecha.",
        )

    return row_to_nutrition_day(row)


@router.put(
    "/{day_date}",
    response_model=NutritionDayResponse,
)
def update_nutrition_day(
    day_date: date,
    nutrition_day: NutritionDayUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> NutritionDayResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE nutrition_days
            SET notes = ?
            WHERE date = ? AND user_id = ?
            """,
            (
                nutrition_day.notes,
                day_date.isoformat(),
                current_user.id,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un registro nutricional para esta fecha.",
            )

        row = connection.execute(
            """
            SELECT id, date, notes
            FROM nutrition_days
            WHERE date = ? AND user_id = ?
            """,
            (day_date.isoformat(), current_user.id),
        ).fetchone()

    return row_to_nutrition_day(row)


@router.delete(
    "/{day_date}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_nutrition_day(
    day_date: date,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM nutrition_days
            WHERE date = ? AND user_id = ?
            """,
            (day_date.isoformat(), current_user.id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un registro nutricional para esta fecha.",
            )

    return Response(status_code=status.HTTP_204_NO_CONTENT)