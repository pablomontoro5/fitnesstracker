import sqlite3
from datetime import date


from fastapi import APIRouter, HTTPException, Response, status


from app.db import get_connection
from app.schemas import (
    NutritionDayCreate,
    NutritionDayResponse,
    NutritionDayUpdate,
)


router = APIRouter(
    prefix="/nutrition-days",
    tags=["nutrition days"],
)


def row_to_nutrition_day(row: sqlite3.Row) -> NutritionDayResponse:
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
) -> NutritionDayResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO nutrition_days (date, notes)
                VALUES (?, ?)
                """,
                (
                    nutrition_day.date.isoformat(),
                    nutrition_day.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT id, date, notes
                FROM nutrition_days
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro nutricional para esta fecha.",
        ) from error

    return row_to_nutrition_day(row)


@router.get(
    "/",
    response_model=list[NutritionDayResponse],
)
def list_nutrition_days() -> list[NutritionDayResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, date, notes
            FROM nutrition_days
            ORDER BY date DESC
            """
        ).fetchall()

    return [row_to_nutrition_day(row) for row in rows]


@router.get(
    "/{day_date}",
    response_model=NutritionDayResponse,
)
def get_nutrition_day(day_date: date) -> NutritionDayResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, date, notes
            FROM nutrition_days
            WHERE date = ?
            """,
            (day_date.isoformat(),),
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
) -> NutritionDayResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE nutrition_days
            SET notes = ?
            WHERE date = ?
            """,
            (
                nutrition_day.notes,
                day_date.isoformat(),
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
            WHERE date = ?
            """,
            (day_date.isoformat(),),
        ).fetchone()

    return row_to_nutrition_day(row)


@router.delete(
    "/{day_date}",
    response_model=None,
)
def delete_nutrition_day(day_date: date) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM nutrition_days
            WHERE date = ?
            """,
            (day_date.isoformat(),),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro nutricional para esta fecha.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)