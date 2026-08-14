from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import initialize_database
from app.routers import (body_metrics, daily_logs, workout_exercises, workout_sessions,workout_sets)


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

app.include_router(daily_logs.router)
app.include_router(body_metrics.router)
app.include_router(workout_sessions.router)
app.include_router(workout_exercises.router)
app.include_router(workout_sets.router)
@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}