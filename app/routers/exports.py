from pathlib import Path

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.db import DatabaseConfigError
from app.dependencies import get_current_user
from app.logging_config import logger
from app.schemas import UserResponse
from app.services import exports


router = APIRouter(
    prefix="/exports",
    tags=["exports"],
)


def delete_export_file(export_path: Path) -> None:
    export_path.unlink(missing_ok=True)


@router.get(
    "/fitness-tracker.json",
    response_class=FileResponse,
)
def download_fitness_tracker_export(
    current_user: UserResponse = Depends(get_current_user),
) -> FileResponse:
    try:
        export_path = exports.create_data_export(user_id=current_user.id)
    except (psycopg.Error, DatabaseConfigError):
        logger.exception("Exportación: fallo de base de datos")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pueden leer tus datos ahora mismo. "
                "Inténtalo de nuevo en unos minutos."
            ),
        )
    except OSError:
        logger.exception("Exportación: no se pudo escribir el fichero")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "No se pudo preparar el archivo de exportación en el "
                "servidor. Si se repite, avisa al administrador."
            ),
        )

    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/json",
        # No dejamos en el servidor copias de datos personales ya entregados.
        background=BackgroundTask(delete_export_file, export_path),
    )
