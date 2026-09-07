from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services import backups


router = APIRouter(
    prefix="/backups",
    tags=["backups"],
)


@router.post(
    "/database",
    response_class=FileResponse,
)
def download_database_backup() -> FileResponse:
    backup_path = backups.create_database_backup()

    return FileResponse(
        path=backup_path,
        filename=backup_path.name,
        media_type="application/octet-stream",
    )