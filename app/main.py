from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.db import check_database, close_pool, initialize_database
from app.invitations import get_registration_mode
from app.logging_config import configure_logging, logger
from app.security import get_jwt_secret
from app.routers import (
    auth,
    body_metrics,
    calendar,
    daily_logs,
    exercise_catalog,
    exports,
    goals,
    food_library,
    meal_templates,
    nutrition_days,
    nutrition_foods,
    nutrition_meals,
    planned_workouts,
    recovery,
    restores,
    runs,
    statistics,
    workout_exercises,
    workout_progress,
    workout_sessions,
    workout_sets,
    workout_templates,
)


FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


DOCS_ENV = "FITNESS_TRACKER_ENABLE_DOCS"


def docs_enabled() -> bool:
    """/docs y /redoc publican el mapa completo de la API: apagados salvo
    que se pida expresamente (desarrollo)."""
    return os.environ.get(DOCS_ENV, "").strip().lower() in {"1", "true", "yes"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Falla al arrancar, no en la primera petición, si la configuración
    # es insegura o inválida.
    configure_logging()
    get_jwt_secret()
    registration_mode = get_registration_mode()
    initialize_database()
    logger.info(
        "Arranque: registro=%s docs=%s",
        registration_mode,
        "activadas" if docs_enabled() else "desactivadas",
    )
    yield
    close_pool()


app = FastAPI(
    title="Fitness Tracker API",
    description="API para registrar actividad, gimnasio, running, nutrición, recuperación y métricas corporales.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled() else None,
    redoc_url="/redoc" if docs_enabled() else None,
    openapi_url="/openapi.json" if docs_enabled() else None,
)

app.include_router(nutrition_meals.router)
app.include_router(nutrition_days.router)
app.include_router(nutrition_foods.router)
app.include_router(daily_logs.router)
app.include_router(body_metrics.router)
app.include_router(workout_sessions.router)
app.include_router(workout_exercises.router)
app.include_router(workout_sets.router)
app.include_router(workout_progress.router)
app.include_router(runs.router)
app.include_router(statistics.router)
app.include_router(exports.router)
app.include_router(restores.router)
app.include_router(workout_templates.router)
app.include_router(goals.router)
app.include_router(recovery.router)
app.include_router(auth.router)
app.include_router(exercise_catalog.router)
app.include_router(planned_workouts.router)
app.include_router(calendar.router)
app.include_router(food_library.router)
app.include_router(meal_templates.router)
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="static",
)


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manifest.webmanifest", include_in_schema=False)
def serve_manifest() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@app.get("/sw.js", include_in_schema=False)
def serve_service_worker() -> FileResponse:
    # Va en la raíz (no en /static/) para que su ámbito sea toda la aplicación,
    # y sin caché para que una versión nueva se instale en la siguiente visita.
    return FileResponse(
        FRONTEND_DIR / "sw.js",
        media_type="text/javascript",
        headers={
            "Cache-Control": "no-cache",
            "Service-Worker-Allowed": "/",
        },
    )


@app.get("/health", tags=["system"])
def health_check() -> JSONResponse:
    """Responde 200 solo si la aplicación y la base de datos funcionan; con
    503, el healthcheck de Docker y los monitores detectan la caída. No se
    devuelve el motivo del fallo (va al log) para no filtrar datos de conexión."""
    try:
        check_database()
    except Exception:
        logger.exception("Healthcheck: la base de datos no responde")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )

    return JSONResponse(content={"status": "ok", "database": "ok"})
