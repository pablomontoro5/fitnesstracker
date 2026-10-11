"""Comidas planificadas: asignar una plantilla de comida a un día y, al hacerla,
registrarla en el diario de nutrición de ese día."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import Connection, get_connection
from app.dependencies import get_current_user
from app.schemas import (
    PlannedMealComplete,
    PlannedMealCompleteResponse,
    PlannedMealCreate,
    PlannedMealResponse,
    PlannedMealUpdate,
    PlannedWeekCopy,
    PlannedWeekCopyResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/planned-meals",
    tags=["planned meals"],
)

MAX_COPY_WEEK_OFFSET_DAYS = 366

# Los totales salen de los elementos de la plantilla (macros por 100 g por su
# cantidad); una plantilla sin elementos o sin plantilla no tiene totales.
SELECT_PLANNED_MEAL = """
    SELECT
        m.id, m.scheduled_date, m.meal_template_id, m.name, m.notes,
        m.status, m.nutrition_meal_id,
        totals.calories, totals.protein_g, totals.carbs_g, totals.fat_g
    FROM planned_meals AS m
    LEFT JOIN (
        SELECT
            meal_template_id,
            SUM(calories_per_100g * quantity_g / 100) AS calories,
            SUM(protein_per_100g * quantity_g / 100) AS protein_g,
            SUM(carbs_per_100g * quantity_g / 100) AS carbs_g,
            SUM(fat_per_100g * quantity_g / 100) AS fat_g
        FROM meal_template_items
        GROUP BY meal_template_id
    ) AS totals ON totals.meal_template_id = m.meal_template_id
"""


def _rounded(value) -> float:
    return round(value or 0, 2)


def row_to_planned_meal(row: dict) -> PlannedMealResponse:
    has_template = row["meal_template_id"] is not None

    return PlannedMealResponse(
        id=row["id"],
        scheduled_date=date.fromisoformat(row["scheduled_date"]),
        meal_template_id=row["meal_template_id"],
        name=row["name"],
        notes=row["notes"],
        status=row["status"],
        nutrition_meal_id=row["nutrition_meal_id"],
        calories=_rounded(row["calories"]) if has_template else None,
        protein_g=_rounded(row["protein_g"]) if has_template else None,
        carbs_g=_rounded(row["carbs_g"]) if has_template else None,
        fat_g=_rounded(row["fat_g"]) if has_template else None,
    )


def get_owned_planned_meal(
    connection: Connection, *, planned_meal_id: int, user_id: int,
) -> dict:
    row = connection.execute(
        SELECT_PLANNED_MEAL + " WHERE m.id = ? AND m.user_id = ?",
        (planned_meal_id, user_id),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una comida planificada con ese id.",
        )

    return row


def get_owned_meal_template(
    connection: Connection, *, template_id: int, user_id: int,
) -> dict:
    template = connection.execute(
        "SELECT id, name FROM meal_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    ).fetchone()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una plantilla de comida con ese id.",
        )

    return template


@router.post(
    "/copy-week",
    response_model=PlannedWeekCopyResponse,
)
def copy_planned_meals_week(
    copy: PlannedWeekCopy,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedWeekCopyResponse:
    """Repite las comidas planificadas de una semana en otra, como
    «planificadas». No duplica: si el día de destino ya tiene una comida con
    el mismo nombre y la misma plantilla, se omite."""
    offset = (copy.target_start - copy.source_start).days

    if offset == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La semana de origen y la de destino deben ser distintas.",
        )

    if abs(offset) > MAX_COPY_WEEK_OFFSET_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Las semanas no pueden estar separadas más de 366 días.",
        )

    source_end = copy.source_start + timedelta(days=6)
    target_end = copy.target_start + timedelta(days=6)

    with get_connection() as connection:
        source_rows = connection.execute(
            """
            SELECT scheduled_date, meal_template_id, name, notes
            FROM planned_meals
            WHERE user_id = ? AND scheduled_date BETWEEN ? AND ?
            ORDER BY scheduled_date ASC, id ASC
            """,
            (
                current_user.id,
                copy.source_start.isoformat(),
                source_end.isoformat(),
            ),
        ).fetchall()

        existing = {
            (row["scheduled_date"], row["meal_template_id"], row["name"].casefold())
            for row in connection.execute(
                """
                SELECT scheduled_date, meal_template_id, name
                FROM planned_meals
                WHERE user_id = ? AND scheduled_date BETWEEN ? AND ?
                """,
                (
                    current_user.id,
                    copy.target_start.isoformat(),
                    target_end.isoformat(),
                ),
            ).fetchall()
        }

        copied = skipped = 0

        for row in source_rows:
            new_date = (
                date.fromisoformat(row["scheduled_date"]) + timedelta(days=offset)
            ).isoformat()
            key = (new_date, row["meal_template_id"], row["name"].casefold())

            if key in existing:
                skipped += 1
                continue

            connection.execute(
                """
                INSERT INTO planned_meals (
                    user_id, scheduled_date, meal_template_id, name, notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    current_user.id, new_date, row["meal_template_id"],
                    row["name"], row["notes"],
                ),
            )
            existing.add(key)
            copied += 1

    return PlannedWeekCopyResponse(copied=copied, skipped=skipped)


@router.post(
    "/",
    response_model=PlannedMealResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_planned_meal(
    planned_meal: PlannedMealCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedMealResponse:
    name = planned_meal.name.strip() if planned_meal.name is not None else None

    if name is not None and not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre de la comida planificada no puede estar vacío.",
        )

    with get_connection() as connection:
        if planned_meal.meal_template_id is not None:
            template = get_owned_meal_template(
                connection,
                template_id=planned_meal.meal_template_id,
                user_id=current_user.id,
            )
            name = name or template["name"]
        elif name is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Debes indicar una plantilla o un nombre para planificar "
                    "la comida."
                ),
            )

        cursor = connection.execute(
            """
            INSERT INTO planned_meals (
                user_id, scheduled_date, meal_template_id, name, notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                planned_meal.scheduled_date.isoformat(),
                planned_meal.meal_template_id,
                name,
                planned_meal.notes,
            ),
        )
        row = get_owned_planned_meal(
            connection,
            planned_meal_id=cursor.lastrowid,
            user_id=current_user.id,
        )

    return row_to_planned_meal(row)


@router.get(
    "/",
    response_model=list[PlannedMealResponse],
)
def list_planned_meals(
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: UserResponse = Depends(get_current_user),
) -> list[PlannedMealResponse]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    conditions = ["m.user_id = ?"]
    parameters: list[object] = [current_user.id]

    if start_date is not None:
        conditions.append("m.scheduled_date >= ?")
        parameters.append(start_date.isoformat())

    if end_date is not None:
        conditions.append("m.scheduled_date <= ?")
        parameters.append(end_date.isoformat())

    with get_connection() as connection:
        rows = connection.execute(
            SELECT_PLANNED_MEAL
            + f" WHERE {' AND '.join(conditions)}"
            + " ORDER BY m.scheduled_date ASC, m.id ASC",
            parameters,
        ).fetchall()

    return [row_to_planned_meal(row) for row in rows]


@router.get(
    "/{planned_meal_id}",
    response_model=PlannedMealResponse,
)
def get_planned_meal(
    planned_meal_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedMealResponse:
    with get_connection() as connection:
        row = get_owned_planned_meal(
            connection,
            planned_meal_id=planned_meal_id,
            user_id=current_user.id,
        )

    return row_to_planned_meal(row)


@router.put(
    "/{planned_meal_id}",
    response_model=PlannedMealResponse,
)
def update_planned_meal(
    planned_meal_id: int,
    planned_meal: PlannedMealUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedMealResponse:
    with get_connection() as connection:
        existing = get_owned_planned_meal(
            connection,
            planned_meal_id=planned_meal_id,
            user_id=current_user.id,
        )

        if existing["status"] == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede modificar una comida planificada completada.",
            )

        if planned_meal.meal_template_id is not None:
            get_owned_meal_template(
                connection,
                template_id=planned_meal.meal_template_id,
                user_id=current_user.id,
            )

        name = planned_meal.name.strip()

        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El nombre de la comida planificada no puede estar vacío.",
            )

        connection.execute(
            """
            UPDATE planned_meals
            SET
                scheduled_date = ?,
                meal_template_id = ?,
                name = ?,
                notes = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                planned_meal.scheduled_date.isoformat(),
                planned_meal.meal_template_id,
                name,
                planned_meal.notes,
                planned_meal.status,
                planned_meal_id,
                current_user.id,
            ),
        )
        row = get_owned_planned_meal(
            connection,
            planned_meal_id=planned_meal_id,
            user_id=current_user.id,
        )

    return row_to_planned_meal(row)


@router.delete(
    "/{planned_meal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_planned_meal(
    planned_meal_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        existing = get_owned_planned_meal(
            connection,
            planned_meal_id=planned_meal_id,
            user_id=current_user.id,
        )

        if existing["status"] == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede eliminar una comida planificada completada.",
            )

        connection.execute(
            "DELETE FROM planned_meals WHERE id = ? AND user_id = ?",
            (planned_meal_id, current_user.id),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{planned_meal_id}/complete",
    response_model=PlannedMealCompleteResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_planned_meal(
    planned_meal_id: int,
    completion: PlannedMealComplete,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedMealCompleteResponse:
    """Registra la comida en el diario de nutrición: crea el día si no existe,
    añade la comida al final del día y copia en ella los alimentos de la
    plantilla (con sus macros calculadas para la cantidad)."""
    with get_connection() as connection:
        planned = get_owned_planned_meal(
            connection,
            planned_meal_id=planned_meal_id,
            user_id=current_user.id,
        )

        if planned["status"] == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La comida planificada ya está completada.",
            )

        if planned["status"] == "skipped":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede completar una comida planificada omitida.",
            )

        day = (
            completion.completed_date
            or date.fromisoformat(planned["scheduled_date"])
        ).isoformat()

        # Si el día ya existe (o lo crea otra petición a la vez), se reutiliza.
        connection.execute(
            "INSERT INTO nutrition_days (user_id, date) VALUES (?, ?) "
            "ON CONFLICT (user_id, date) DO NOTHING",
            (current_user.id, day),
        )
        nutrition_day_id = connection.execute(
            "SELECT id FROM nutrition_days WHERE user_id = ? AND date = ?",
            (current_user.id, day),
        ).fetchone()["id"]

        position = connection.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 AS next_position "
            "FROM nutrition_meals WHERE nutrition_day_id = ?",
            (nutrition_day_id,),
        ).fetchone()["next_position"]

        nutrition_meal_id = connection.execute(
            "INSERT INTO nutrition_meals (nutrition_day_id, name, position) "
            "VALUES (?, ?, ?)",
            (nutrition_day_id, planned["name"], position),
        ).lastrowid

        items = []

        if planned["meal_template_id"] is not None:
            items = connection.execute(
                """
                SELECT name, quantity_g, calories_per_100g, protein_per_100g,
                       carbs_per_100g, fat_per_100g, notes
                FROM meal_template_items
                WHERE meal_template_id = ?
                ORDER BY position ASC, id ASC
                """,
                (planned["meal_template_id"],),
            ).fetchall()

        for food_position, item in enumerate(items, start=1):
            factor = item["quantity_g"] / 100

            connection.execute(
                """
                INSERT INTO nutrition_foods (
                    nutrition_meal_id, name, quantity_g, calories, protein_g,
                    carbs_g, fat_g, position, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nutrition_meal_id,
                    item["name"],
                    item["quantity_g"],
                    round(item["calories_per_100g"] * factor, 2),
                    round(item["protein_per_100g"] * factor, 2),
                    round(item["carbs_per_100g"] * factor, 2),
                    round(item["fat_per_100g"] * factor, 2),
                    food_position,
                    item["notes"],
                ),
            )

        connection.execute(
            """
            UPDATE planned_meals
            SET status = 'completed', nutrition_meal_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND status = 'planned'
            """,
            (nutrition_meal_id, planned_meal_id, current_user.id),
        )
        row = get_owned_planned_meal(
            connection,
            planned_meal_id=planned_meal_id,
            user_id=current_user.id,
        )

    return PlannedMealCompleteResponse(
        planned_meal=row_to_planned_meal(row),
        nutrition_day_id=nutrition_day_id,
        nutrition_meal_id=nutrition_meal_id,
        foods_added=len(items),
    )
