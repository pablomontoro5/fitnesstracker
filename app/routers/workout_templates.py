import sqlite3
from datetime import date
from fastapi import APIRouter, Depends,HTTPException, Response, status
from app.dependencies import get_current_user

from app.db import get_connection
from app.schemas import (
    UserResponse,
    WorkoutSessionResponse,
    WorkoutTemplateCreate,
    WorkoutTemplateExerciseCreate,
    WorkoutTemplateExerciseResponse,
    WorkoutTemplateExerciseUpdate,
    WorkoutTemplateResponse,
    WorkoutTemplateSetCreate,
    WorkoutTemplateSetResponse,
    WorkoutTemplateSetUpdate,
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


def ensure_workout_template_exists(
    template_id: int,
    user_id: int,
) -> None:
    with get_connection() as connection:
        workout_template = connection.execute(
            """
            SELECT id
            FROM workout_templates
            WHERE id = ?
              AND user_id = ?
            """,
            (
                template_id,
                user_id,
            ),
        ).fetchone()

    if workout_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una plantilla con ese id.",
        )

def row_to_workout_template_set(
    row: sqlite3.Row,
) -> WorkoutTemplateSetResponse:
    return WorkoutTemplateSetResponse(
        id=row["id"],
        workout_template_exercise_id=row[
            "workout_template_exercise_id"
        ],
        set_type=row["set_type"],
        position=row["position"],
        target_rep_range=row["target_rep_range"],
        repetitions=row["repetitions"],
        weight_kg=row["weight_kg"],
        rir=row["rir"],
        notes=row["notes"],
        volume_kg=row["repetitions"] * row["weight_kg"],
    )


def ensure_workout_template_exercise_exists(
    exercise_id: int,
    user_id: int,
) -> None:
    with get_connection() as connection:
        workout_template_exercise = connection.execute(
            """
            SELECT workout_template_exercises.id
            FROM workout_template_exercises
            INNER JOIN workout_templates
                ON workout_templates.id =
                    workout_template_exercises.workout_template_id
            WHERE workout_template_exercises.id = ?
              AND workout_templates.user_id = ?
            """,
            (
                exercise_id,
                user_id,
            ),
        ).fetchone()

    if workout_template_exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un ejercicio de plantilla con ese id.",
        )
@router.post(
    "/",
    response_model=WorkoutTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_template(
    workout_template: WorkoutTemplateCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutTemplateResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO workout_templates (
                user_id,
                name,
                notes
            )
            VALUES (?, ?, ?)
            """,
            (
                current_user.id,
                workout_template.name.strip(),
                workout_template.notes,
            ),
        )

        created_template = connection.execute(
            """
            SELECT
                id,
                name,
                notes
            FROM workout_templates
            WHERE id = ?
              AND user_id = ?
            """,
            (
                cursor.lastrowid,
                current_user.id,
            ),
        ).fetchone()

    return WorkoutTemplateResponse(
        id=created_template["id"],
        name=created_template["name"],
        notes=created_template["notes"],
    )

@router.get(
    "/",
    response_model=list[WorkoutTemplateResponse],
)
def list_workout_templates(
    current_user: UserResponse = Depends(get_current_user),
) -> list[WorkoutTemplateResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                name,
                notes
            FROM workout_templates
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (current_user.id,),
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
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutTemplateResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                name,
                notes
            FROM workout_templates
            WHERE id = ?
              AND user_id = ?
            """,
            (
                template_id,
                current_user.id,
            ),
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
def delete_workout_template(
    template_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_templates
            WHERE id = ?
              AND user_id = ?
            """,
            (
                template_id,
                current_user.id,
            ),
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
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutTemplateExerciseResponse:
    ensure_workout_template_exists(template_id, current_user.id)  # Assuming user_id is 1 for this example

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
    current_user: UserResponse = Depends(get_current_user),
) -> list[WorkoutTemplateExerciseResponse]:
    ensure_workout_template_exists(template_id, current_user.id)  # Assuming user_id is 1 for this example

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
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutTemplateExerciseResponse:
    ensure_workout_template_exercise_exists(exercise_id,current_user.id)  # Assuming user_id is 1 for this example
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
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    ensure_workout_template_exercise_exists(exercise_id, current_user.id)
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

@router.post(
    "/exercises/{exercise_id}/sets/",
    response_model=WorkoutTemplateSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workout_template_set(
    exercise_id: int,
    workout_template_set: WorkoutTemplateSetCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutTemplateSetResponse:
    ensure_workout_template_exercise_exists(exercise_id, current_user.id)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO workout_template_sets (
                    workout_template_exercise_id,
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exercise_id,
                    workout_template_set.set_type,
                    workout_template_set.position,
                    workout_template_set.target_rep_range,
                    workout_template_set.repetitions,
                    workout_template_set.weight_kg,
                    workout_template_set.rir,
                    workout_template_set.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    workout_template_exercise_id,
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                FROM workout_template_sets
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe una serie en esa posición "
                "para este ejercicio de plantilla."
            ),
        ) from error

    return row_to_workout_template_set(row)


@router.get(
    "/exercises/{exercise_id}/sets/",
    response_model=list[WorkoutTemplateSetResponse],
)
def list_workout_template_sets(
    exercise_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> list[WorkoutTemplateSetResponse]:
    ensure_workout_template_exercise_exists(exercise_id, current_user.id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                workout_template_exercise_id,
                set_type,
                position,
                target_rep_range,
                repetitions,
                weight_kg,
                rir,
                notes
            FROM workout_template_sets
            WHERE workout_template_exercise_id = ?
            ORDER BY position ASC
            """,
            (exercise_id,),
        ).fetchall()

    return [
        row_to_workout_template_set(row)
        for row in rows
    ]


@router.put(
    "/sets/{set_id}",
    response_model=WorkoutTemplateSetResponse,
)
def update_workout_template_set(
    set_id: int,
    workout_template_set: WorkoutTemplateSetUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutTemplateSetResponse:
    ensure_workout_template_set_exists(
        set_id,
        current_user.id,
    )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE workout_template_sets
                SET
                    set_type = ?,
                    position = ?,
                    target_rep_range = ?,
                    repetitions = ?,
                    weight_kg = ?,
                    rir = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    workout_template_set.set_type,
                    workout_template_set.position,
                    workout_template_set.target_rep_range,
                    workout_template_set.repetitions,
                    workout_template_set.weight_kg,
                    workout_template_set.rir,
                    workout_template_set.notes,
                    set_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe una serie de plantilla con ese id.",
                )

            row = connection.execute(
                """
                SELECT
                    id,
                    workout_template_exercise_id,
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                FROM workout_template_sets
                WHERE id = ?
                """,
                (set_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ya existe una serie en esa posición "
                "para este ejercicio de plantilla."
            ),
        ) from error

    return row_to_workout_template_set(row)
@router.delete(
    "/sets/{set_id}",
    response_model=None,
)
def delete_workout_template_set(
    set_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    ensure_workout_template_set_exists(
        set_id,
        current_user.id,
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workout_template_sets
            WHERE id = ?
            """,
            (set_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una serie de plantilla con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
@router.post(
    "/{template_id}/create-session",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session_from_workout_template(
    template_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> WorkoutSessionResponse:
    with get_connection() as connection:
        workout_template = connection.execute(
            """
            SELECT
                id,
                name,
                notes
            FROM workout_templates
            WHERE id = ?
            AND user_id = ?
            """,
            (
                template_id,
                current_user.id,
            ),
        ).fetchone()

        if workout_template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una plantilla con ese id.",
            )

        session_cursor = connection.execute(
            """
            INSERT INTO workout_sessions (
                user_id,
                date,
                name,
                notes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                current_user.id,
                date.today().isoformat(),
                workout_template["name"],
                workout_template["notes"],
            ),
        )

        session_id = session_cursor.lastrowid

        template_exercises = connection.execute(
            """
            SELECT
                id,
                name,
                muscle_group,
                position,
                technique_notes
            FROM workout_template_exercises
            WHERE workout_template_id = ?
            ORDER BY position ASC, id ASC
            """,
            (template_id,),
        ).fetchall()

        for template_exercise in template_exercises:
            exercise_cursor = connection.execute(
                """
                INSERT INTO workout_exercises (
                    workout_session_id,
                    name,
                    muscle_group,
                    position,
                    technique_notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    template_exercise["name"],
                    template_exercise["muscle_group"],
                    template_exercise["position"],
                    template_exercise["technique_notes"],
                ),
            )

            exercise_id = exercise_cursor.lastrowid

            template_sets = connection.execute(
                """
                SELECT
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                FROM workout_template_sets
                WHERE workout_template_exercise_id = ?
                ORDER BY position ASC, id ASC
                """,
                (template_exercise["id"],),
            ).fetchall()

            connection.executemany(
                """
                INSERT INTO workout_sets (
                    workout_exercise_id,
                    set_type,
                    position,
                    target_rep_range,
                    repetitions,
                    weight_kg,
                    rir,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        exercise_id,
                        template_set["set_type"],
                        template_set["position"],
                        template_set["target_rep_range"],
                        template_set["repetitions"],
                        template_set["weight_kg"],
                        template_set["rir"],
                        template_set["notes"],
                    )
                    for template_set in template_sets
                ],
            )

        created_session = connection.execute(
            """
            SELECT id, date, name, notes
            FROM workout_sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, current_user.id),
        ).fetchone()

    return WorkoutSessionResponse(
        id=created_session["id"],
        date=date.fromisoformat(created_session["date"]),
        name=created_session["name"],
        notes=created_session["notes"],
    )

def ensure_workout_template_set_exists(
    set_id: int,
    user_id: int,
) -> None:
    with get_connection() as connection:
        workout_template_set = connection.execute(
            """
            SELECT workout_template_sets.id
            FROM workout_template_sets
            INNER JOIN workout_template_exercises
                ON workout_template_exercises.id =
                    workout_template_sets.workout_template_exercise_id
            INNER JOIN workout_templates
                ON workout_templates.id =
                    workout_template_exercises.workout_template_id
            WHERE workout_template_sets.id = ?
              AND workout_templates.user_id = ?
            """,
            (
                set_id,
                user_id,
            ),
        ).fetchone()

    if workout_template_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una serie de plantilla con ese id.",
        )