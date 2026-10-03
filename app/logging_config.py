"""Registros de la aplicación.

Todo va a la salida estándar/error: con Docker se leen con
`docker compose logs` y no hace falta gestionar ficheros. Nunca se escriben
contraseñas, tokens, códigos de invitación ni de recuperación, ni emails;
las cuentas se identifican por su id.
"""
import logging
import os

LOG_LEVEL_ENV = "FITNESS_TRACKER_LOG_LEVEL"
LOGGER_NAME = "fitness_tracker"

logger = logging.getLogger(LOGGER_NAME)


def configure_logging() -> None:
    level_name = os.environ.get(LOG_LEVEL_ENV, "INFO").strip().upper()
    level = logging.getLevelName(level_name)

    if not isinstance(level, int):
        level = logging.INFO

    logger.setLevel(level)

    if not any(getattr(h, "_fitness_tracker", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        handler._fitness_tracker = True  # type: ignore[attr-defined]
        logger.addHandler(handler)

    # Un solo registro: si no, el logger raíz de uvicorn lo duplicaría.
    logger.propagate = False
