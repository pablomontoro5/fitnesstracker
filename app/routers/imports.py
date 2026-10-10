from typing import Callable

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.db import Connection, IntegrityError, get_connection
from app.dependencies import get_current_user
from app.logging_config import logger
from app.schemas import UserResponse
from app.services.hevy_import import import_hevy_workouts
from app.services.strong_import import import_strong_workouts
from app.services.workout_import import InvalidImport

MAX_IMPORT_BYTES = 10 * 1024 * 1024


router = APIRouter(
    prefix="/imports",
    tags=["imports"],
)


def run_import(
    source: str,
    file: UploadFile,
    dry_run: bool,
    user: UserResponse,
    importer: Callable[[Connection, bytes], dict],
) -> dict:
    """Valida el archivo y ejecuta `importer` en una transacción: o se guarda
    todo o no se guarda nada."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Debes seleccionar el archivo .csv exportado desde {source}.",
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
        with get_connection() as connection:
            result = importer(connection, content)
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
            "Importación de %s: usuario=%s sesiones=%s series=%s",
            source, user.id, result["sessions"], result["sets"],
        )

    return result


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
    return run_import(
        "Hevy", file, dry_run, current_user,
        lambda connection, content: import_hevy_workouts(
            connection, current_user.id, content, dry_run=dry_run,
        ),
    )


@router.post(
    "/strong",
    status_code=status.HTTP_200_OK,
)
def import_strong_csv(
    file: UploadFile = File(...),
    weight_unit: str = Form("kg"),
    dry_run: bool = Form(True),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Importa a la cuenta autenticada los entrenamientos de un CSV de Strong.

    El CSV de Strong no indica la unidad del peso: `weight_unit` es «kg» o
    «lb». Solo añade datos; con `dry_run` (por defecto) no guarda nada."""
    return run_import(
        "Strong", file, dry_run, current_user,
        lambda connection, content: import_strong_workouts(
            connection, current_user.id, content,
            weight_unit=weight_unit, dry_run=dry_run,
        ),
    )
