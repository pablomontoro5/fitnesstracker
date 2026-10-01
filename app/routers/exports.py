from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.dependencies import get_current_user
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
    export_path = exports.create_data_export(user_id=current_user.id)

    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/json",
        # No dejamos en el servidor copias de datos personales ya entregados.
        background=BackgroundTask(delete_export_file, export_path),
    )
