"""Plantillas de comidas privadas por usuario.

Requiere meal_templates(id, user_id, name, notes, updated_at) y
meal_template_items(id, template_id, food_id, grams). Los alimentos
se obtienen de food_library(id, user_id, name, calories_per_100g,
protein_per_100g, carbs_per_100g, fat_per_100g).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.db import get_connection
from app.dependencies import get_current_user

router = APIRouter(prefix="/meal-templates", tags=["meal templates"])


class TemplateData(BaseModel):
    name: str = Field(min_length=1)
    notes: str | None = None


class ItemData(BaseModel):
    food_id: int = Field(gt=0)
    grams: float = Field(gt=0)


class ItemResponse(ItemData):
    id: int
    name: str
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
        "SELECT id FROM food_library WHERE id = ? AND user_id = ?",
        (food_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Alimento no encontrado.")
    return row


def _response(db, template_id: int, user_id: int) -> TemplateResponse:
    template = _template(db, template_id, user_id)
    rows = db.execute(
        """
        SELECT i.id, i.food_id, i.grams, f.name,
               f.calories_per_100g, f.protein_per_100g,
               f.carbs_per_100g, f.fat_per_100g
        FROM meal_template_items AS i
        JOIN food_library AS f ON f.id = i.food_id AND f.user_id = ?
        WHERE i.template_id = ?
        ORDER BY i.id
        """,
        (user_id, template_id),
    ).fetchall()
    items = [
        ItemResponse(
            id=row["id"], food_id=row["food_id"], grams=row["grams"],
            name=row["name"],
            calories=row["calories_per_100g"] * row["grams"] / 100,
            protein=row["protein_per_100g"] * row["grams"] / 100,
            carbs=row["carbs_per_100g"] * row["grams"] / 100,
            fat=row["fat_per_100g"] * row["grams"] / 100,
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
            "SELECT id FROM meal_templates WHERE user_id = ? ORDER BY name COLLATE NOCASE, id",
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
        db.execute("DELETE FROM meal_template_items WHERE template_id = ?", (template_id,))
        db.execute(
            "DELETE FROM meal_templates WHERE id = ? AND user_id = ?",
            (template_id, user.id),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/items", response_model=TemplateResponse, status_code=201)
def add_item(template_id: int, data: ItemData, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)
        _food(db, data.food_id, user.id)
        db.execute(
            "INSERT INTO meal_template_items (template_id, food_id, grams) VALUES (?, ?, ?)",
            (template_id, data.food_id, data.grams),
        )
        result = _response(db, template_id, user.id)
    return result


@router.put("/{template_id}/items/{item_id}", response_model=TemplateResponse)
def update_item(template_id: int, item_id: int, data: ItemData, user=Depends(get_current_user)):
    with get_connection() as db:
        _template(db, template_id, user.id)
        _food(db, data.food_id, user.id)
        cursor = db.execute(
            """UPDATE meal_template_items SET food_id = ?, grams = ?
               WHERE id = ? AND template_id = ?""",
            (data.food_id, data.grams, item_id, template_id),
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
            "DELETE FROM meal_template_items WHERE id = ? AND template_id = ?",
            (item_id, template_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Elemento no encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)