from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.db import IntegrityError, get_connection
from app.dependencies import get_current_user
from app.logging_config import logger
from app.schemas import UserResponse
from app.services.hevy_import import InvalidImport, import_hevy_workouts

MAX_IMPORT_BYTES = 10 * 1024 * 1024


router = APIRouter(
    prefix="/imports",
    tags=["imports"],
)


@router.post(
    "/hevy",
    status_code=status.HTTP_200_OK,
)
def import_hevy_csv(
    file: UploadFile = File(...),
    dry_run: bool = Form(True),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Importa a la cuenta autenticada los entrenamientos de un CSV de Hevy.

    Solo añade datos. Con `dry_run` (por defecto) devuelve lo que haría sin
    guardar nada, para revisarlo antes de confirmar."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar el archivo .csv exportado desde Hevy.",
        )

    try:
        content = file.file.read(MAX_IMPORT_BYTES + 1)
    finally:
        file.file.close()

    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="El archivo es demasiado grande.",
        )

    try:
        # Una sola transacción: si algo falla, no se guarda nada.
        with get_connection() as connection:
            result = import_hevy_workouts(
                connection, current_user.id, content, dry_run=dry_run,
            )
    except InvalidImport as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El archivo contiene datos que la aplicación no admite "
                f"({error}). No se ha importado nada."
            ),
        ) from error

    if not dry_run:
        logger.info(
            "Importación de Hevy: usuario=%s sesiones=%s series=%s",
            current_user.id, result["sessions"], result["sets"],
        )

    return result
