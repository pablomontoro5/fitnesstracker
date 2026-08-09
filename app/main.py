from fastapi import FastAPI
from app.db import initialize_database
app = FastAPI(
    title="Fitness Tracker API",
    description="API para registrar actividad, gimnasio, running, nutrición y métricas corporales.",
    version="0.1.0",
)

@app.on_event("startup")
def startup() -> None:
    initialize_database()

@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}