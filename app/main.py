from contextlib import asynccontextmanager

from fastapi import FastAPI

app = FastAPI(
    title="Fitness Tracker API",
    description="API para registrar actividad, gimnasio, running, nutrición y métricas corporales.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(daily_logs.router)

@app.on_event("startup")
def startup() -> None:
    initialize_database()

@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}