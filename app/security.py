import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash


JWT_SECRET_ENV = "FITNESS_TRACKER_JWT_SECRET"
JWT_ALGORITHM_ENV = "FITNESS_TRACKER_JWT_ALGORITHM"
ACCESS_TOKEN_MINUTES_ENV = "FITNESS_TRACKER_ACCESS_TOKEN_MINUTES"

DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_MINUTES = 60
TEST_JWT_SECRET = "fitness-tracker-test-secret"


password_hash = PasswordHash.recommended()


def get_jwt_secret() -> str:
    secret = os.environ.get(JWT_SECRET_ENV)

    if secret:
        return secret

    if os.environ.get("FITNESS_TRACKER_TESTING") == "1":
        return TEST_JWT_SECRET

    raise RuntimeError(
        f"{JWT_SECRET_ENV} debe estar configurada fuera del entorno de pruebas."
    )


def get_jwt_algorithm() -> str:
    return os.environ.get(JWT_ALGORITHM_ENV, DEFAULT_JWT_ALGORITHM)


def get_access_token_minutes() -> int:
    value = os.environ.get(
        ACCESS_TOKEN_MINUTES_ENV,
        str(DEFAULT_ACCESS_TOKEN_MINUTES),
    )

    try:
        minutes = int(value)
    except ValueError as error:
        raise RuntimeError(
            f"{ACCESS_TOKEN_MINUTES_ENV} debe ser un entero positivo."
        ) from error

    if minutes <= 0:
        raise RuntimeError(
            f"{ACCESS_TOKEN_MINUTES_ENV} debe ser un entero positivo."
        )

    return minutes


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=get_access_token_minutes()
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=get_jwt_algorithm(),
    )


def decode_access_token(token: str) -> int:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acceso inválido o caducado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
        )
        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise credentials_exception

        return int(subject)
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_exception