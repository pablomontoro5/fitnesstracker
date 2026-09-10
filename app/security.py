import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash


JWT_SECRET_ENV = "FITNESS_TRACKER_JWT_SECRET"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES_ENV = "FITNESS_TRACKER_ACCESS_TOKEN_MINUTES"
DEFAULT_ACCESS_TOKEN_MINUTES = 60


password_hash = PasswordHash.recommended()


def get_jwt_secret() -> str:
    secret = os.environ.get(JWT_SECRET_ENV)

    if not secret:
        raise RuntimeError(
            f"La variable de entorno {JWT_SECRET_ENV} debe estar configurada."
        )

    return secret


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

    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": expires_at,
        },
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def get_user_id_from_token(token: str) -> int:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acceso inválido o caducado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
        )
        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise credentials_exception

        return int(subject)
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_exception