import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import (
    WorkoutTemplateCreate,
    WorkoutTemplateExerciseCreate,
    WorkoutTemplateExerciseResponse,
    WorkoutTemplateExerciseUpdate,
    WorkoutTemplateResponse,
)


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

def row_to_workout_template_exercise(
    row: sqlite3.Row,
) -> WorkoutTemplateExerciseResponse:
    return WorkoutTemplateExerciseResponse(
        id=row["id"],
        workout_template_id=row["workout_template_id"],
        name=row["name"],
        muscle_group=row["muscle_group"],
        position=row["position"],
        technique_notes=row["technique_notes"],
    )


def ensure_workout_template_exists(template_id: int) -> None:
    with get_connection() as connection:
        workout_template = connection.execute(
            """
            SELECT id
            FROM workout_templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()

    if workout_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una plantilla con ese id.",
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
@router.post(
    "/{template_id}/exercises/",
    response_model=WorkoutTemplateExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_template_exercise(
    template_id: int,
    workout_template_exercise: WorkoutTemplateExerciseCreate,
) -> WorkoutTemplateExerciseResponse:
    ensure_workout_template_exists(template_id)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO workout_template_exercises (
                    workout_template_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    workout_template_exercise.name.strip(),
                    workout_template_exercise.muscle_group.strip(),
                    workout_template_exercise.position,
                    workout_template_exercise.technique_notes,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    workout_template_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                FROM workout_template_exercises
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe un ejercicio en esa posición "
                "para esta plantilla."
            ),
        ) from error

    return row_to_workout_template_exercise(row)


@router.get(
    "/{template_id}/exercises/",
    response_model=list[WorkoutTemplateExerciseResponse],
)
def list_workout_template_exercises(
    template_id: int,
) -> list[WorkoutTemplateExerciseResponse]:
    ensure_workout_template_exists(template_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                workout_template_id,
                name,
                muscle_group,
                position,
                technique_notes
            FROM workout_template_exercises
            WHERE workout_template_id = ?
            ORDER BY position ASC
            """,
            (template_id,),
        ).fetchall()

    return [
        row_to_workout_template_exercise(row)
        for row in rows
    ]


@router.put(
    "/exercises/{exercise_id}",
    response_model=WorkoutTemplateExerciseResponse,
)
def update_workout_template_exercise(
    exercise_id: int,
    workout_template_exercise: WorkoutTemplateExerciseUpdate,
) -> WorkoutTemplateExerciseResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE workout_template_exercises
                SET
                    name = ?,
                    muscle_group = ?,
                    position = ?,
                    technique_notes = ?
                WHERE id = ?
                """,
                (
                    workout_template_exercise.name.strip(),
                    workout_template_exercise.muscle_group.strip(),
                    workout_template_exercise.position,
                    workout_template_exercise.technique_notes,
                    exercise_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe un ejercicio de plantilla con ese id.",
                )

            row = connection.execute(
                """
                SELECT
                    id,
                    workout_template_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                FROM workout_template_exercises
                WHERE id = ?
                """,
                (exercise_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe un ejercicio en esa posición "
                "para esta plantilla."
            ),
        ) from error

    return row_to_workout_template_exercise(row)


@router.delete(
    "/exercises/{exercise_id}",
    response_model=None,
)
def delete_workout_template_exercise(
    exercise_id: int,
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_template_exercises
            WHERE id = ?
            """,
            (exercise_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio de plantilla con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)