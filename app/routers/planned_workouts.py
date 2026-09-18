import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.dependencies import get_current_user
from app.schemas import (
    PlannedWorkoutComplete,
    PlannedWorkoutCompleteResponse,
    PlannedWorkoutCreate,
    PlannedWorkoutResponse,
    PlannedWorkoutUpdate,
    UserResponse,
    WorkoutSessionResponse,
)


router = APIRouter(
    prefix="/planned-workouts",
    tags=["planned workouts"],
)


def row_to_planned_workout(row: sqlite3.Row) -> PlannedWorkoutResponse:
    return PlannedWorkoutResponse(
        id=row["id"],
        scheduled_date=date.fromisoformat(row["scheduled_date"]),
        workout_template_id=row["workout_template_id"],
        name=row["name"],
        notes=row["notes"],
        status=row["status"],
        workout_session_id=row["workout_session_id"],
    )


def get_owned_workout_template(
    connection: sqlite3.Connection,
    *,
    template_id: int,
    user_id: int,
) -> sqlite3.Row:
    template = connection.execute(
        """
        SELECT
            id,
            name,
            notes
        FROM workout_templates
        WHERE id = ?
          AND user_id = ?
        """,
        (template_id, user_id),
    ).fetchone()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una plantilla con ese id.",
        )

    return template


def get_owned_planned_workout(
    connection: sqlite3.Connection,
    *,
    planned_workout_id: int,
    user_id: int,
) -> sqlite3.Row:
    planned_workout = connection.execute(
        """
        SELECT
            id,
            scheduled_date,
            workout_template_id,
            name,
            notes,
            status,
            workout_session_id
        FROM planned_workouts
        WHERE id = ?
          AND user_id = ?
        """,
        (planned_workout_id, user_id),
    ).fetchone()

    if planned_workout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una sesión planificada con ese id.",
        )

    return planned_workout


def resolve_planned_workout_name(
    connection: sqlite3.Connection,
    *,
    workout_template_id: int | None,
    name: str | None,
    user_id: int,
) -> str:
    normalized_name = name.strip() if name is not None else None

    if normalized_name is not None and not normalized_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre de la sesión planificada no puede estar vacío.",
        )

    if workout_template_id is None:
        if normalized_name is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Debes indicar una plantilla o un nombre para "
                    "planificar la sesión."
                ),
            )
        return normalized_name

    template = get_owned_workout_template(
        connection,
        template_id=workout_template_id,
        user_id=user_id,
    )

    return normalized_name or template["name"]


@router.post(
    "/",
    response_model=PlannedWorkoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_planned_workout(
    planned_workout: PlannedWorkoutCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedWorkoutResponse:
    with get_connection() as connection:
        name = resolve_planned_workout_name(
            connection,
            workout_template_id=planned_workout.workout_template_id,
            name=planned_workout.name,
            user_id=current_user.id,
        )

        cursor = connection.execute(
            """
            INSERT INTO planned_workouts (
                user_id,
                scheduled_date,
                workout_template_id,
                name,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                planned_workout.scheduled_date.isoformat(),
                planned_workout.workout_template_id,
                name,
                planned_workout.notes,
            ),
        )

        row = get_owned_planned_workout(
            connection,
            planned_workout_id=cursor.lastrowid,
            user_id=current_user.id,
        )

    return row_to_planned_workout(row)


@router.get(
    "/",
    response_model=list[PlannedWorkoutResponse],
)
def list_planned_workouts(
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: UserResponse = Depends(get_current_user),
) -> list[PlannedWorkoutResponse]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    conditions = ["user_id = ?"]
    parameters: list[object] = [current_user.id]

    if start_date is not None:
        conditions.append("scheduled_date >= ?")
        parameters.append(start_date.isoformat())

    if end_date is not None:
        conditions.append("scheduled_date <= ?")
        parameters.append(end_date.isoformat())

    where_clause = " AND ".join(conditions)

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                scheduled_date,
                workout_template_id,
                name,
                notes,
                status,
                workout_session_id
            FROM planned_workouts
            WHERE {where_clause}
            ORDER BY scheduled_date ASC, id ASC
            """,
            parameters,
        ).fetchall()

    return [row_to_planned_workout(row) for row in rows]


@router.get(
    "/{planned_workout_id}",
    response_model=PlannedWorkoutResponse,
)
def get_planned_workout(
    planned_workout_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedWorkoutResponse:
    with get_connection() as connection:
        row = get_owned_planned_workout(
            connection,
            planned_workout_id=planned_workout_id,
            user_id=current_user.id,
        )

    return row_to_planned_workout(row)


@router.put(
    "/{planned_workout_id}",
    response_model=PlannedWorkoutResponse,
)
def update_planned_workout(
    planned_workout_id: int,
    planned_workout: PlannedWorkoutUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedWorkoutResponse:
    with get_connection() as connection:
        existing = get_owned_planned_workout(
            connection,
            planned_workout_id=planned_workout_id,
            user_id=current_user.id,
        )

        if existing["status"] == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede modificar una sesión planificada completada.",
            )

        if planned_workout.workout_template_id is not None:
            get_owned_workout_template(
                connection,
                template_id=planned_workout.workout_template_id,
                user_id=current_user.id,
            )

        name = planned_workout.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El nombre de la sesión planificada no puede estar vacío.",
            )

        connection.execute(
            """
            UPDATE planned_workouts
            SET
                scheduled_date = ?,
                workout_template_id = ?,
                name = ?,
                notes = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND user_id = ?
            """,
            (
                planned_workout.scheduled_date.isoformat(),
                planned_workout.workout_template_id,
                name,
                planned_workout.notes,
                planned_workout.status,
                planned_workout_id,
                current_user.id,
            ),
        )

        row = get_owned_planned_workout(
            connection,
            planned_workout_id=planned_workout_id,
            user_id=current_user.id,
        )

    return row_to_planned_workout(row)


@router.delete(
    "/{planned_workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_planned_workout(
    planned_workout_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        existing = get_owned_planned_workout(
            connection,
            planned_workout_id=planned_workout_id,
            user_id=current_user.id,
        )

        if existing["status"] == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede eliminar una sesión planificada completada.",
            )

        connection.execute(
            """
            DELETE FROM planned_workouts
            WHERE id = ?
              AND user_id = ?
            """,
            (planned_workout_id, current_user.id),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{planned_workout_id}/complete",
    response_model=PlannedWorkoutCompleteResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_planned_workout(
    planned_workout_id: int,
    completion: PlannedWorkoutComplete,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedWorkoutCompleteResponse:
    with get_connection() as connection:
        planned_workout = get_owned_planned_workout(
            connection,
            planned_workout_id=planned_workout_id,
            user_id=current_user.id,
        )

        if planned_workout["status"] == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La sesión planificada ya está completada.",
            )

        if planned_workout["status"] == "skipped":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede completar una sesión planificada omitida.",
            )

        completed_date = completion.completed_date or date.fromisoformat(
            planned_workout["scheduled_date"]
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
                completed_date.isoformat(),
                planned_workout["name"],
                planned_workout["notes"],
            ),
        )
        workout_session_id = session_cursor.lastrowid

        if planned_workout["workout_template_id"] is not None:
            template = get_owned_workout_template(
                connection,
                template_id=planned_workout["workout_template_id"],
                user_id=current_user.id,
            )

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
                (template["id"],),
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
                        workout_session_id,
                        template_exercise["name"],
                        template_exercise["muscle_group"],
                        template_exercise["position"],
                        template_exercise["technique_notes"],
                    ),
                )
                workout_exercise_id = exercise_cursor.lastrowid

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
                            workout_exercise_id,
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

        connection.execute(
            """
            UPDATE planned_workouts
            SET
                status = 'completed',
                workout_session_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND user_id = ?
              AND status = 'planned'
            """,
            (
                workout_session_id,
                planned_workout_id,
                current_user.id,
            ),
        )

        completed_planned_workout = get_owned_planned_workout(
            connection,
            planned_workout_id=planned_workout_id,
            user_id=current_user.id,
        )

        workout_session = connection.execute(
            """
            SELECT
                id,
                date,
                name,
                notes
            FROM workout_sessions
            WHERE id = ?
              AND user_id = ?
            """,
            (workout_session_id, current_user.id),
        ).fetchone()

    return PlannedWorkoutCompleteResponse(
        planned_workout=row_to_planned_workout(completed_planned_workout),
        workout_session=WorkoutSessionResponse(
            id=workout_session["id"],
            date=date.fromisoformat(workout_session["date"]),
            name=workout_session["name"],
            notes=workout_session["notes"],
        ),
    )