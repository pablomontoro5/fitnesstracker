from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import Connection, get_connection
from app.dependencies import get_current_user
from app.routers.runs import calculate_average_pace
from app.schemas import (
    PlannedWeekCopy,
    PlannedWeekCopyResponse,
    PlannedWorkoutComplete,
    PlannedWorkoutCompleteResponse,
    PlannedWorkoutCreate,
    PlannedWorkoutResponse,
    PlannedWorkoutUpdate,
    RunResponse,
    UserResponse,
    WorkoutSessionResponse,
)


router = APIRouter(
    prefix="/planned-workouts",
    tags=["planned workouts"],
)


def row_to_planned_workout(row: dict) -> PlannedWorkoutResponse:
    return PlannedWorkoutResponse(
        id=row["id"],
        scheduled_date=date.fromisoformat(row["scheduled_date"]),
        kind=row["kind"],
        target_distance_km=row["target_distance_km"],
        workout_template_id=row["workout_template_id"],
        name=row["name"],
        notes=row["notes"],
        status=row["status"],
        workout_session_id=row["workout_session_id"],
        run_id=row["run_id"],
    )


def get_owned_workout_template(
    connection: Connection,
    *,
    template_id: int,
    user_id: int,
) -> dict:
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
    connection: Connection,
    *,
    planned_workout_id: int,
    user_id: int,
) -> dict:
    planned_workout = connection.execute(
        """
        SELECT
            id,
            scheduled_date,
            kind,
            target_distance_km,
            workout_template_id,
            name,
            notes,
            status,
            workout_session_id,
            run_id
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
    connection: Connection,
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


def complete_planned_run(
    connection: Connection,
    *,
    planned_workout: dict,
    completion: PlannedWorkoutComplete,
    completed_date: date,
    user_id: int,
) -> PlannedWorkoutCompleteResponse:
    """Completa una carrera planificada creando su registro de running."""
    distance_km = completion.distance_km or planned_workout["target_distance_km"]

    if completion.duration_seconds is None or distance_km is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Para completar una carrera indica su duración y, si no "
                "tenía distancia objetivo, su distancia."
            ),
        )

    run_id = connection.execute(
        """
        INSERT INTO runs (
            user_id, date, distance_km, duration_seconds,
            average_pace_seconds_km, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            completed_date.isoformat(),
            distance_km,
            completion.duration_seconds,
            calculate_average_pace(
                distance_km=distance_km,
                duration_seconds=completion.duration_seconds,
            ),
            planned_workout["notes"],
        ),
    ).lastrowid

    connection.execute(
        """
        UPDATE planned_workouts
        SET status = 'completed', run_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ? AND status = 'planned'
        """,
        (run_id, planned_workout["id"], user_id),
    )

    completed = get_owned_planned_workout(
        connection,
        planned_workout_id=planned_workout["id"],
        user_id=user_id,
    )
    run = connection.execute(
        """
        SELECT id, date, distance_km, duration_seconds,
               average_pace_seconds_km, notes
        FROM runs
        WHERE id = ? AND user_id = ?
        """,
        (run_id, user_id),
    ).fetchone()

    return PlannedWorkoutCompleteResponse(
        planned_workout=row_to_planned_workout(completed),
        run=RunResponse(
            id=run["id"],
            date=date.fromisoformat(run["date"]),
            distance_km=run["distance_km"],
            duration_seconds=run["duration_seconds"],
            average_pace_seconds_km=run["average_pace_seconds_km"],
            notes=run["notes"],
        ),
    )


MAX_COPY_WEEK_OFFSET_DAYS = 366
DEFAULT_RUN_NAME = "Carrera"


@router.post(
    "/copy-week",
    response_model=PlannedWeekCopyResponse,
)
def copy_planned_week(
    copy: PlannedWeekCopy,
    current_user: UserResponse = Depends(get_current_user),
) -> PlannedWeekCopyResponse:
    """Repite una semana de planificación en otra.

    Copia todas las sesiones de los 7 días de origen a los mismos días de
    destino, como «planificadas» (aunque en origen estuvieran completadas u
    omitidas). Si el día de destino ya tiene una sesión igual (mismo nombre y
    misma plantilla), no se duplica."""
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
            SELECT scheduled_date, kind, target_distance_km,
                   workout_template_id, name, notes
            FROM planned_workouts
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
            (
                row["scheduled_date"], row["kind"],
                row["workout_template_id"], row["name"].casefold(),
            )
            for row in connection.execute(
                """
                SELECT scheduled_date, kind, workout_template_id, name
                FROM planned_workouts
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
            key = (
                new_date, row["kind"], row["workout_template_id"],
                row["name"].casefold(),
            )

            if key in existing:
                skipped += 1
                continue

            connection.execute(
                """
                INSERT INTO planned_workouts (
                    user_id, scheduled_date, kind, target_distance_km,
                    workout_template_id, name, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    new_date,
                    row["kind"],
                    row["target_distance_km"],
                    row["workout_template_id"],
                    row["name"],
                    row["notes"],
                ),
            )
            existing.add(key)
            copied += 1

    return PlannedWeekCopyResponse(copied=copied, skipped=skipped)


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
        if planned_workout.kind == "run":
            name = (planned_workout.name or DEFAULT_RUN_NAME).strip()

            if not name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="El nombre de la carrera no puede estar vacío.",
                )
        else:
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
                kind,
                target_distance_km,
                workout_template_id,
                name,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user.id,
                planned_workout.scheduled_date.isoformat(),
                planned_workout.kind,
                planned_workout.target_distance_km,
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
                kind,
                target_distance_km,
                workout_template_id,
                name,
                notes,
                status,
                workout_session_id,
                run_id
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

        if existing["kind"] == "run":
            if planned_workout.workout_template_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Una carrera planificada no usa plantilla.",
                )
        elif planned_workout.target_distance_km is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La distancia objetivo solo se indica en las carreras.",
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
                target_distance_km = ?,
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
                planned_workout.target_distance_km,
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

        if planned_workout["kind"] == "run":
            return complete_planned_run(
                connection,
                planned_workout=planned_workout,
                completion=completion,
                completed_date=completed_date,
                user_id=current_user.id,
            )

        if completion.distance_km is not None or completion.duration_seconds is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Solo las carreras llevan distancia y duración.",
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