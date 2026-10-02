import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_connection
from app.invitations import (
    consume_invitation,
    find_valid_invitation_id,
    get_registration_mode,
)
from app.rate_limit import (
    LOGIN_FAILURES_PER_ACCOUNT,
    LOGIN_FAILURES_PER_IP,
    REGISTER_ATTEMPTS_PER_IP,
    get_client_ip,
    too_many_requests,
)
from app.schemas import (
    AccessTokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.security import (
    create_access_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

bearer_scheme = HTTPBearer(auto_error=False)


def row_to_user(row: sqlite3.Row) -> UserResponse:
    return UserResponse(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserResponse:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token de acceso.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = get_user_id_from_token(credentials.credentials)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, display_name, is_active, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None or not bool(row["is_active"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta no está disponible.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return row_to_user(row)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user: UserRegister, request: Request) -> UserResponse:
    client_ip = get_client_ip(request)
    retry_after = REGISTER_ATTEMPTS_PER_IP.retry_after(client_ip)

    if retry_after:
        raise too_many_requests(retry_after)

    REGISTER_ATTEMPTS_PER_IP.record(client_ip)

    email = user.email.strip().lower()
    display_name = user.display_name.strip()
    requires_invitation = get_registration_mode() == "invite"

    try:
        with get_connection() as connection:
            invitation_id = (
                find_valid_invitation_id(connection, user.invite_code)
                if requires_invitation
                else None
            )

            cursor = connection.execute(
                """
                INSERT INTO users (email, display_name, password_hash)
                VALUES (?, ?, ?)
                """,
                (
                    email,
                    display_name,
                    hash_password(user.password),
                ),
            )

            if invitation_id is not None:
                consume_invitation(
                    connection,
                    invitation_id,
                    cursor.lastrowid,
                )

            row = connection.execute(
                """
                SELECT id, email, display_name, is_active, created_at
                FROM users
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email.",
        ) from error

    return row_to_user(row)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
)
def login_user(user: UserLogin, request: Request) -> AccessTokenResponse:
    email = user.email.strip().lower()
    client_ip = get_client_ip(request)
    account_key = f"{client_ip}|{email}"

    for limiter, key in (
        (LOGIN_FAILURES_PER_ACCOUNT, account_key),
        (LOGIN_FAILURES_PER_IP, client_ip),
    ):
        retry_after = limiter.retry_after(key)

        if retry_after:
            raise too_many_requests(retry_after)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, password_hash, is_active
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if row is None or not verify_password(user.password, row["password_hash"]):
        LOGIN_FAILURES_PER_ACCOUNT.record(account_key)
        LOGIN_FAILURES_PER_IP.record(client_ip)
        raise invalid_credentials

    LOGIN_FAILURES_PER_ACCOUNT.reset(account_key)

    if not bool(row["is_active"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta no está disponible.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AccessTokenResponse(
        access_token=create_access_token(row["id"]),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_authenticated_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return current_user