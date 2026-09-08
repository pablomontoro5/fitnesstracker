from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services.restores import restore_database


router = APIRouter(
    prefix="/restores",
    tags=["restores"],
)


@router.post(
    "/database",
    status_code=status.HTTP_200_OK,
)
def restore_database_backup(
    file: UploadFile = File(...),
) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".db"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar un archivo con extensión .db.",
        )

    try:
        backup_path = restore_database(upload=file)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    finally:
        file.file.close()

    return {
        "message": "Base de datos restaurada correctamente.",
        "safety_backup_filename": backup_path.name,
    }
