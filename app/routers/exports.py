from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services import exports


router = APIRouter(
    prefix="/exports",
    tags=["exports"],
)


@router.get(
    "/fitness-tracker.json",
    response_class=FileResponse,
)
def download_fitness_tracker_export() -> FileResponse:
    export_path = exports.create_data_export()

    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/json",
    )