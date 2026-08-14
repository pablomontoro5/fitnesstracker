import sqlite3
from datetime import date

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.schemas import BodyMetricCreate, BodyMetricResponse

router = APIRouter(
    prefix="/body-metrics",
    tags=["body metrics"],
)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 2)

def row_to_body_metric(row: sqlite3.Row) -> BodyMetricResponse:
    return BodyMetricResponse(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        weight_kg=row["weight_kg"],
        height_cm=row["height_cm"],
        bmi=row["bmi"],
        notes=row["notes"],
    )
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
                INSERT INTO body_metrics (date, weight_kg, height_cm, bmi, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    body_metric.date.isoformat(),
                    body_metric.weight_kg,
                    body_metric.height_cm,
                    bmi,
                    body_metric.notes,
                ),
            )

            row = connection.execute(
                """
                SELECT id, date, weight_kg, height_cm, bmi, notes
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
            """
            SELECT id, date, weight_kg, height_cm, bmi, notes
            FROM body_metrics
            ORDER BY date DESC
            """
        ).fetchall()

    return [row_to_body_metric(row) for row in rows]


@router.get("/{metric_id}", response_model=BodyMetricResponse)
def get_body_metric(metric_id: int) -> BodyMetricResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, date, weight_kg, height_cm, bmi, notes
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


@router.delete(
    "/{metric_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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