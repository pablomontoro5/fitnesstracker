from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.dependencies import require_admin
from app.schemas import UserResponse
from app.services import backups


router = APIRouter(
    prefix="/backups",
    tags=["backups"],
)


@router.post(
    "/database",
    response_class=FileResponse,
)
def download_database_backup(
    _admin: UserResponse = Depends(require_admin),
) -> FileResponse:
    # La copia incluye a todos los usuarios y sus hashes de contraseña:
    # solo administradores.
    backup_path = backups.create_database_backup()

    return FileResponse(
        path=backup_path,
        filename=backup_path.name,
        media_type="application/octet-stream",
    )