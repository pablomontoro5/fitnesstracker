from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import initialize_database
from app.routers import (
    auth,
    backups,
    body_metrics,
    daily_logs,
    exports,
    goals,
    nutrition_days,
    nutrition_foods,
    nutrition_meals,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Fitness Tracker API",
    description="API para registrar actividad, gimnasio, running, nutrición y métricas corporales.",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(backups.router)
app.include_router(exports.router)
app.include_router(restores.router)
app.include_router(workout_templates.router)
app.include_router(goals.router)
app.include_router(recovery.router)
app.include_router(auth.router)
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="static",
)


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}