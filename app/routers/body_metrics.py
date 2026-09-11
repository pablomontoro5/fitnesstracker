import sqlite3
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db import get_connection
from app.schemas import (
    BodyCompositionChanges,
    BodyCompositionProgressRecord,
    BodyCompositionProgressResponse,
    BodyMetricCreate,
    BodyMetricResponse,
    BodyMetricUpdate,
)


router = APIRouter(
    prefix="/body-metrics",
    tags=["body metrics"],
)


BODY_METRIC_SELECT_COLUMNS = """
    id,
    date,
    weight_kg,
    height_cm,
    bmi,
    body_fat_percentage,
    waist_cm,
    hip_cm,
    chest_cm,
    arm_cm,
    thigh_cm,
    notes
"""


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 2)


def calculate_fat_mass_kg(
    weight_kg: float,
    body_fat_percentage: float | None,
) -> float | None:
    if body_fat_percentage is None:
        return None

    return round(weight_kg * body_fat_percentage / 100, 2)


def calculate_lean_mass_kg(
    weight_kg: float,
    body_fat_percentage: float | None,
) -> float | None:
    fat_mass_kg = calculate_fat_mass_kg(
        weight_kg,
        body_fat_percentage,
    )

    if fat_mass_kg is None:
        return None

    return round(weight_kg - fat_mass_kg, 2)


def row_to_body_metric(row: sqlite3.Row) -> BodyMetricResponse:
    body_fat_percentage = row["body_fat_percentage"]

    return BodyMetricResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        weight_kg=row["weight_kg"],
        height_cm=row["height_cm"],
        bmi=row["bmi"],
        body_fat_percentage=body_fat_percentage,
        fat_mass_kg=calculate_fat_mass_kg(
            row["weight_kg"],
            body_fat_percentage,
        ),
        lean_mass_kg=calculate_lean_mass_kg(
            row["weight_kg"],
            body_fat_percentage,
        ),
        waist_cm=row["waist_cm"],
        hip_cm=row["hip_cm"],
        chest_cm=row["chest_cm"],
        arm_cm=row["arm_cm"],
        thigh_cm=row["thigh_cm"],
        notes=row["notes"],
    )


def row_to_composition_record(
    row: sqlite3.Row,
) -> BodyCompositionProgressRecord:
    body_fat_percentage = row["body_fat_percentage"]

    return BodyCompositionProgressRecord(
        date=date.fromisoformat(row["date"]),
        weight_kg=row["weight_kg"],
        bmi=row["bmi"],
        body_fat_percentage=body_fat_percentage,
        fat_mass_kg=calculate_fat_mass_kg(
            row["weight_kg"],
            body_fat_percentage,
        ),
        lean_mass_kg=calculate_lean_mass_kg(
            row["weight_kg"],
            body_fat_percentage,
        ),
        waist_cm=row["waist_cm"],
        hip_cm=row["hip_cm"],
        chest_cm=row["chest_cm"],
        arm_cm=row["arm_cm"],
        thigh_cm=row["thigh_cm"],
    )


def calculate_change(
    records: list[BodyCompositionProgressRecord],
    attribute_name: str,
) -> float | None:
    values = [
        getattr(record, attribute_name)
        for record in records
        if getattr(record, attribute_name) is not None
    ]

    if len(values) < 2:
        return None

    return round(values[-1] - values[0], 2)


@router.post(
    "/",
    response_model=BodyMetricResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_body_metric(body_metric: BodyMetricCreate) -> BodyMetricResponse:
    bmi = calculate_bmi(
        weight_kg=body_metric.weight_kg,
        height_cm=body_metric.height_cm,
    )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO body_metrics (
                    date,
                    weight_kg,
                    height_cm,
                    bmi,
                    body_fat_percentage,
                    waist_cm,
                    hip_cm,
                    chest_cm,
                    arm_cm,
                    thigh_cm,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    body_metric.date.isoformat(),
                    body_metric.weight_kg,
                    body_metric.height_cm,
                    bmi,
                    body_metric.body_fat_percentage,
                    body_metric.waist_cm,
                    body_metric.hip_cm,
                    body_metric.chest_cm,
                    body_metric.arm_cm,
                    body_metric.thigh_cm,
                    body_metric.notes,
                ),
            )

            row = connection.execute(
                f"""
                SELECT {BODY_METRIC_SELECT_COLUMNS}
                FROM body_metrics
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una medición para esta fecha.",
        ) from error

    return row_to_body_metric(row)


@router.get("/", response_model=list[BodyMetricResponse])
def list_body_metrics() -> list[BodyMetricResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT {BODY_METRIC_SELECT_COLUMNS}
            FROM body_metrics
            ORDER BY date DESC
            """
        ).fetchall()

    return [row_to_body_metric(row) for row in rows]


@router.get(
    "/progress",
    response_model=BodyCompositionProgressResponse,
)
def get_body_composition_progress(
    start_date: date = Query(
        description="Fecha inicial del periodo, incluida.",
    ),
    end_date: date = Query(
        description="Fecha final del periodo, incluida.",
    ),
) -> BodyCompositionProgressResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date no puede ser posterior a end_date.",
        )

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT {BODY_METRIC_SELECT_COLUMNS}
            FROM body_metrics
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (
                start_date.isoformat(),
                end_date.isoformat(),
            ),
        ).fetchall()

    records = [row_to_composition_record(row) for row in rows]

    return BodyCompositionProgressResponse(
        start_date=start_date,
        end_date=end_date,
        records=records,
        changes=BodyCompositionChanges(
            weight_kg=calculate_change(records, "weight_kg"),
            bmi=calculate_change(records, "bmi"),
            body_fat_percentage=calculate_change(
                records,
                "body_fat_percentage",
            ),
            fat_mass_kg=calculate_change(records, "fat_mass_kg"),
            lean_mass_kg=calculate_change(records, "lean_mass_kg"),
            waist_cm=calculate_change(records, "waist_cm"),
            hip_cm=calculate_change(records, "hip_cm"),
            chest_cm=calculate_change(records, "chest_cm"),
            arm_cm=calculate_change(records, "arm_cm"),
            thigh_cm=calculate_change(records, "thigh_cm"),
        ),
    )


@router.get("/{metric_id}", response_model=BodyMetricResponse)
def get_body_metric(metric_id: int) -> BodyMetricResponse:
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT {BODY_METRIC_SELECT_COLUMNS}
            FROM body_metrics
            WHERE id = ?
            """,
            (metric_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una medición con ese id.",
        )

    return row_to_body_metric(row)


@router.put(
    "/{metric_id}",
    response_model=BodyMetricResponse,
)
def update_body_metric(
    metric_id: int,
    body_metric: BodyMetricUpdate,
) -> BodyMetricResponse:
    bmi = calculate_bmi(
        weight_kg=body_metric.weight_kg,
        height_cm=body_metric.height_cm,
    )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE body_metrics
                SET
                    date = ?,
                    weight_kg = ?,
                    height_cm = ?,
                    bmi = ?,
                    body_fat_percentage = ?,
                    waist_cm = ?,
                    hip_cm = ?,
                    chest_cm = ?,
                    arm_cm = ?,
                    thigh_cm = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    body_metric.date.isoformat(),
                    body_metric.weight_kg,
                    body_metric.height_cm,
                    bmi,
                    body_metric.body_fat_percentage,
                    body_metric.waist_cm,
                    body_metric.hip_cm,
                    body_metric.chest_cm,
                    body_metric.arm_cm,
                    body_metric.thigh_cm,
                    body_metric.notes,
                    metric_id,
                ),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No existe una medición con ese id.",
                )

            row = connection.execute(
                f"""
                SELECT {BODY_METRIC_SELECT_COLUMNS}
                FROM body_metrics
                WHERE id = ?
                """,
                (metric_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una medición para esta fecha.",
        ) from error

    return row_to_body_metric(row)


@router.delete(
    "/{metric_id}",
    response_model=None,
)
def delete_body_metric(metric_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM body_metrics
            WHERE id = ?
            """,
            (metric_id,),
        )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una medición con ese id.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)