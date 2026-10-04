"""Plantillas de comidas privadas por usuario.

Cada elemento guarda una copia (nombre y macros por 100 g) del alimento de la
biblioteca en el momento de añadirlo: editar o borrar después el alimento no
altera las plantillas ya creadas.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.db import get_connection
from app.dependencies import get_current_user

router = APIRouter(prefix="/meal-templates", tags=["meal templates"])


class TemplateData(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class ItemData(BaseModel):
    food_id: int = Field(gt=0)
    grams: float = Field(gt=0, le=100_000)


class ItemUpdate(BaseModel):
    grams: float = Field(gt=0, le=100_000)
    # Si se indica, el elemento pasa a copiar los datos de ese alimento.
    food_id: int | None = Field(default=None, gt=0)


class ItemResponse(BaseModel):
    id: int
    name: str
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float


class TemplateResponse(TemplateData):
    id: int
    items: list[ItemResponse]
    calories: float
    protein: float
    carbs: float
    fat: float


def _name(value: str) -> str:
    result = value.strip()
    if not result:
        raise HTTPException(status_code=422, detail="El nombre no puede estar vacío.")
    return result


def _template(db, template_id: int, user_id: int):
    row = db.execute(
        "SELECT id, name, notes FROM meal_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada.")
    return row


def _food(db, food_id: int, user_id: int):
    row = db.execute(
        """SELECT id, name, calories_per_100g, protein_per_100g,
                  carbs_per_100g, fat_per_100g
           FROM food_library WHERE id = ? AND user_id = ?""",
        (food_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Alimento no encontrado.")
    return row


def _response(db, template_id: int, user_id: int) -> TemplateResponse:
    template = _template(db, template_id, user_id)
    rows = db.execute(
        """
        SELECT id, name, quantity_g, calories_per_100g, protein_per_100g,
               carbs_per_100g, fat_per_100g
        FROM meal_template_items
        WHERE meal_template_id = ?
        ORDER BY position, id
        """,
        (template_id,),
    ).fetchall()
    items = [
        ItemResponse(
            id=row["id"], name=row["name"], grams=row["quantity_g"],
            calories=row["calories_per_100g"] * row["quantity_g"] / 100,
            protein=row["protein_per_100g"] * row["quantity_g"] / 100,
            carbs=row["carbs_per_100g"] * row["quantity_g"] / 100,
            fat=row["fat_per_100g"] * row["quantity_g"] / 100,
        )
        for row in rows
    ]
    return TemplateResponse(
        id=template["id"], name=template["name"], notes=template["notes"],
        items=items,
        calories=sum(item.calories for item in items),
        protein=sum(item.protein for item in items),
        carbs=sum(item.carbs for item in items),
        fat=sum(item.fat for item in items),
    )


@router.post("/", response_model=TemplateResponse, status_code=201)
def create_template(data: TemplateData, user=Depends(get_current_user)):
    with get_connection() as db:
        cursor = db.execute(
            "INSERT INTO meal_templates (user_id, name, notes) VALUES (?, ?, ?)",
            (user.id, _name(data.name), data.notes),
        )
        result = _response(db, cursor.lastrowid, user.id)
    return result


@router.get("/", response_model=list[TemplateResponse])
def list_templates(user=Depends(get_current_user)):
    with get_connection() as db:
        rows = db.execute(
            "SELECT id FROM meal_templates WHERE user_id = ? ORDER BY LOWER(name), id",
            (user.id,),
        ).fetchall()
        return [_response(db, row["id"], user.id) for row in rows]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int, user=Depends(get_current_user)):
    with get_connection() as db:
        return _response(db, template_id, user.id)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(template_id: int, data: TemplateData, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)
        db.execute(
            """UPDATE meal_templates SET name = ?, notes = ?,
               updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?""",
            (_name(data.name), data.notes, template_id, user.id),
        )
        result = _response(db, template_id, user.id)
    return result


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)
        # Los elementos se borran en cascada.
        db.execute(
            "DELETE FROM meal_templates WHERE id = ? AND user_id = ?",
            (template_id, user.id),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/items", response_model=TemplateResponse, status_code=201)
def add_item(template_id: int, data: ItemData, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)
        food = _food(db, data.food_id, user.id)
        position = db.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 AS next_position "
            "FROM meal_template_items WHERE meal_template_id = ?",
            (template_id,),
        ).fetchone()["next_position"]
        db.execute(
            """INSERT INTO meal_template_items
               (meal_template_id, name, quantity_g, calories_per_100g,
                protein_per_100g, carbs_per_100g, fat_per_100g, position)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                template_id, food["name"], data.grams,
                food["calories_per_100g"], food["protein_per_100g"],
                food["carbs_per_100g"], food["fat_per_100g"], position,
            ),
        )
        result = _response(db, template_id, user.id)
    return result


@router.put("/{template_id}/items/{item_id}", response_model=TemplateResponse)
def update_item(template_id: int, item_id: int, data: ItemUpdate, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)

        if data.food_id is None:
            cursor = db.execute(
                """UPDATE meal_template_items SET quantity_g = ?
                   WHERE id = ? AND meal_template_id = ?""",
                (data.grams, item_id, template_id),
            )
        else:
            food = _food(db, data.food_id, user.id)
            cursor = db.execute(
                """UPDATE meal_template_items
                   SET name = ?, quantity_g = ?, calories_per_100g = ?,
                       protein_per_100g = ?, carbs_per_100g = ?,
                       fat_per_100g = ?
                   WHERE id = ? AND meal_template_id = ?""",
                (
                    food["name"], data.grams, food["calories_per_100g"],
                    food["protein_per_100g"], food["carbs_per_100g"],
                    food["fat_per_100g"], item_id, template_id,
                ),
            )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Elemento no encontrado.")
        result = _response(db, template_id, user.id)
    return result


@router.delete("/{template_id}/items/{item_id}", status_code=204)
def delete_item(template_id: int, item_id: int, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)
        cursor = db.execute(
            "DELETE FROM meal_template_items WHERE id = ? AND meal_template_id = ?",
            (item_id, template_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Elemento no encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
