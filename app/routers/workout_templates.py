import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import WorkoutTemplateCreate, WorkoutTemplateResponse


router = APIRouter(
    prefix="/workout-templates",
    tags=["workout templates"],
)


def row_to_workout_template(
    row: sqlite3.Row,
) -> WorkoutTemplateResponse:
    return WorkoutTemplateResponse(
        id=row["id"],
        name=row["name"],
        notes=row["notes"],
    )


@router.post(
    "/",
    response_model=WorkoutTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_template(
    workout_template: WorkoutTemplateCreate,
) -> WorkoutTemplateResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO workout_templates (name, notes)
            VALUES (?, ?)
            """,
            (
                workout_template.name.strip(),
                workout_template.notes,
            ),
        )

        row = connection.execute(
            """
            SELECT id, name, notes
            FROM workout_templates
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return row_to_workout_template(row)


@router.get(
    "/",
    response_model=list[WorkoutTemplateResponse],
)
def list_workout_templates() -> list[WorkoutTemplateResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, notes
            FROM workout_templates
            ORDER BY id DESC
            """
        ).fetchall()

    return [
        row_to_workout_template(row)
        for row in rows
    ]


@router.get(
    "/{template_id}",
    response_model=WorkoutTemplateResponse,
)
def get_workout_template(
    template_id: int,
) -> WorkoutTemplateResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, notes
            FROM workout_templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una plantilla con ese id.",
        )

    return row_to_workout_template(row)


@router.delete(
    "/{template_id}",
    response_model=None,
)
def delete_workout_template(template_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_templates
            WHERE id = ?
            """,
            (template_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una plantilla con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)