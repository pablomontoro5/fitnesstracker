import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.logging_config import logger
from app.db import IntegrityError, get_connection
from app.dependencies import get_current_user
from app.schemas import UserResponse
from app.routers.auth import get_verified_password_row
from app.services.account_restore import InvalidExport, restore_account_data

MAX_ACCOUNT_RESTORE_BYTES = 20 * 1024 * 1024


router = APIRouter(
    prefix="/restores",
    tags=["restores"],
)


@router.post(
    "/account",
    status_code=status.HTTP_200_OK,
)
def restore_account_from_export(
    file: UploadFile = File(...),
    password: str = Form(...),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Sustituye los datos de la cuenta autenticada por los de su exportación
    JSON. No toca a ningún otro usuario."""
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar un archivo .json exportado por la aplicación.",
        )

    try:
        content = file.file.read(MAX_ACCOUNT_RESTORE_BYTES + 1)
    finally:
        file.file.close()

    if len(content) > MAX_ACCOUNT_RESTORE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="El archivo es demasiado grande.",
        )

    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es un JSON válido.",
        ) from error

    try:
        # Una sola transacción: si algo falla, no cambia nada.
        with get_connection() as connection:
            get_verified_password_row(connection, current_user.id, password)
            counts = restore_account_data(connection, current_user.id, data)
    except InvalidExport as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El archivo contiene datos no válidos o repetidos "
                f"({error}). No se ha cambiado nada."
            ),
        ) from error

    logger.warning(
        "Datos de la cuenta restaurados desde exportación: id=%s %s",
        current_user.id,
        counts,
    )

    return {
        "message": "Datos de la cuenta restaurados correctamente.",
        "restored": counts,
    }
