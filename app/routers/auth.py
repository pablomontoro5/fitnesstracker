
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import Connection, IntegrityError, get_connection
from app.logging_config import logger
from app.invitations import (
    consume_invitation,
    find_valid_invitation_id,
    get_registration_mode,
)
from app.password_resets import (
    consume_password_reset,
    find_valid_reset_id,
    invalid_reset,
)
from app.rate_limit import (
    LOGIN_FAILURES_PER_ACCOUNT,
    LOGIN_FAILURES_PER_IP,
    PASSWORD_FAILURES_PER_USER,
    REGISTER_ATTEMPTS_PER_IP,
    RESET_ATTEMPTS_PER_IP,
    get_client_ip,
    too_many_requests,
)
from app.schemas import (
    AccessTokenResponse,
    AccountDelete,
    PasswordChange,
    PasswordReset,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.security import (
    create_access_token,
    get_token_claims,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

bearer_scheme = HTTPBearer(auto_error=False)


def row_to_user(row: dict) -> UserResponse:
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

    user_id, token_version = get_token_claims(credentials.credentials)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, display_name, is_active, created_at,
                   token_version
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    # Cambiar o restablecer la contraseña sube token_version y deja de
    # valer cualquier token emitido antes.
    if (
        row is None
        or not bool(row["is_active"])
        or row["token_version"] != token_version
    ):
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
    except IntegrityError as error:
        logger.info("Registro: email ya existente ip=%s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email.",
        ) from error

    logger.info("Registro: cuenta creada id=%s ip=%s", row["id"], client_ip)

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
            SELECT id, password_hash, is_active, token_version
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
        logger.warning(
            "Login fallido: cuenta=%s ip=%s",
            "desconocida" if row is None else f"id={row['id']}",
            client_ip,
        )
        raise invalid_credentials

    LOGIN_FAILURES_PER_ACCOUNT.reset(account_key)

    if not bool(row["is_active"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta no está disponible.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Login correcto: id=%s ip=%s", row["id"], client_ip)

    return AccessTokenResponse(
        access_token=create_access_token(row["id"], row["token_version"]),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_authenticated_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return current_user


def check_password_attempts(user_id: int) -> str:
    key = f"user:{user_id}"
    retry_after = PASSWORD_FAILURES_PER_USER.retry_after(key)

    if retry_after:
        raise too_many_requests(retry_after)

    return key


def get_verified_password_row(
    connection: Connection,
    user_id: int,
    password: str,
) -> dict:
    """Comprueba la contraseña actual; cuenta los fallos para limitarlos."""
    key = check_password_attempts(user_id)

    row = connection.execute(
        """
        SELECT id, password_hash, token_version
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if row is None or not verify_password(password, row["password_hash"]):
        PASSWORD_FAILURES_PER_USER.record(key)
        logger.warning("Contraseña actual incorrecta: id=%s", user_id)

        # 400 y no 401: un 401 haría que el frontend cerrara la sesión.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )

    PASSWORD_FAILURES_PER_USER.reset(key)

    return row


@router.post(
    "/change-password",
    response_model=AccessTokenResponse,
)
def change_password(
    payload: PasswordChange,
    current_user: UserResponse = Depends(get_current_user),
) -> AccessTokenResponse:
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser distinta de la actual.",
        )

    with get_connection() as connection:
        row = get_verified_password_row(
            connection,
            current_user.id,
            payload.current_password,
        )
        new_version = row["token_version"] + 1

        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, token_version = ?
            WHERE id = ?
            """,
            (hash_password(payload.new_password), new_version, row["id"]),
        )

    logger.info("Contraseña cambiada: id=%s", current_user.id)

    # Las demás sesiones se cierran; esta continúa con el token nuevo.
    return AccessTokenResponse(
        access_token=create_access_token(current_user.id, new_version),
    )


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reset_password(payload: PasswordReset, request: Request) -> Response:
    client_ip = get_client_ip(request)
    retry_after = RESET_ATTEMPTS_PER_IP.retry_after(client_ip)

    if retry_after:
        raise too_many_requests(retry_after)

    RESET_ATTEMPTS_PER_IP.record(client_ip)

    email = payload.email.strip().lower()

    with get_connection() as connection:
        user_row = connection.execute(
            """
            SELECT id, is_active, token_version
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if user_row is None or not bool(user_row["is_active"]):
            logger.warning("Recuperación fallida: cuenta inexistente ip=%s", client_ip)
            raise invalid_reset()

        try:
            reset_id = find_valid_reset_id(
                connection,
                user_row["id"],
                payload.code,
            )
        except HTTPException:
            logger.warning(
                "Recuperación fallida: código inválido id=%s ip=%s",
                user_row["id"],
                client_ip,
            )
            raise

        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, token_version = ?
            WHERE id = ?
            """,
            (
                hash_password(payload.new_password),
                user_row["token_version"] + 1,
                user_row["id"],
            ),
        )
        consume_password_reset(connection, reset_id)

    logger.info("Contraseña restablecida con código: id=%s ip=%s", user_row["id"], client_ip)

    # Tras restablecer, un bloqueo por intentos fallidos ya no tiene sentido.
    LOGIN_FAILURES_PER_ACCOUNT.reset(f"{client_ip}|{email}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_account(
    payload: AccountDelete,
    current_user: UserResponse = Depends(get_current_user),
) -> Response:
    with get_connection() as connection:
        get_verified_password_row(
            connection,
            current_user.id,
            payload.password,
        )

        # Todas las tablas de datos dependen de users con ON DELETE CASCADE,
        # así que se borra la cuenta y todo lo suyo.
        connection.execute(
            "DELETE FROM users WHERE id = ?",
            (current_user.id,),
        )

    logger.info("Cuenta eliminada: id=%s", current_user.id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
