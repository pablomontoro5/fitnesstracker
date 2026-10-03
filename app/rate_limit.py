"""Limitador de intentos en memoria (ventana deslizante).

Pensado para una sola instancia del servidor. Con varios procesos cada uno
llevaría su propia cuenta, así que el límite real se multiplicaría.
"""
import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status


MAX_TRACKED_KEYS = 10_000


class RateLimiter:
    def __init__(
        self,
        max_attempts: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float] | None:
        attempts = self._attempts.get(key)

        if attempts is None:
            return None

        while attempts and now - attempts[0] >= self.window_seconds:
            attempts.popleft()

        if not attempts:
            del self._attempts[key]
            return None

        return attempts

    def retry_after(self, key: str) -> int:
        """Segundos que faltan para poder reintentar; 0 si no hay bloqueo."""
        with self._lock:
            now = self._clock()
            attempts = self._prune(key, now)

            if attempts is None or len(attempts) < self.max_attempts:
                return 0

            return max(
                1,
                math.ceil(self.window_seconds - (now - attempts[0])),
            )

    def record(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._prune(key, now)
            self._attempts.setdefault(key, deque()).append(now)

            if len(self._attempts) > MAX_TRACKED_KEYS:
                self._evict(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()

    def _evict(self, now: float) -> None:
        for key in list(self._attempts):
            self._prune(key, now)

        # Si siguen sobrando claves, se descartan las más antiguas.
        while len(self._attempts) > MAX_TRACKED_KEYS:
            self._attempts.pop(next(iter(self._attempts)))


LOGIN_FAILURES_PER_ACCOUNT = RateLimiter(max_attempts=5, window_seconds=15 * 60)
LOGIN_FAILURES_PER_IP = RateLimiter(max_attempts=20, window_seconds=15 * 60)
REGISTER_ATTEMPTS_PER_IP = RateLimiter(max_attempts=10, window_seconds=60 * 60)
# Contraseña actual incorrecta al cambiarla o al borrar la cuenta.
PASSWORD_FAILURES_PER_USER = RateLimiter(max_attempts=5, window_seconds=15 * 60)
RESET_ATTEMPTS_PER_IP = RateLimiter(max_attempts=10, window_seconds=15 * 60)


def reset_rate_limits() -> None:
    for limiter in (
        LOGIN_FAILURES_PER_ACCOUNT,
        LOGIN_FAILURES_PER_IP,
        REGISTER_ATTEMPTS_PER_IP,
        PASSWORD_FAILURES_PER_USER,
        RESET_ATTEMPTS_PER_IP,
    ):
        limiter.clear()


def get_client_ip(request: Request) -> str:
    # Detrás de un proxy hay que arrancar uvicorn con --proxy-headers para
    # que esto sea la IP real y no la del proxy.
    return request.client.host if request.client else "unknown"


def too_many_requests(retry_after_seconds: int) -> HTTPException:
    minutes = math.ceil(retry_after_seconds / 60)

    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "Demasiados intentos. Inténtalo de nuevo en "
            f"{minutes} minuto{'s' if minutes != 1 else ''}."
        ),
        headers={"Retry-After": str(retry_after_seconds)},
    )
