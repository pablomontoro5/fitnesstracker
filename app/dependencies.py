import os

from fastapi import Depends, HTTPException, status

from app.routers.auth import get_current_user
from app.schemas import UserResponse


ADMIN_EMAILS_ENV = "FITNESS_TRACKER_ADMIN_EMAILS"


def get_admin_emails() -> set[str]:
    """Emails con rol de administrador, definidos por entorno.

    Si la variable no existe o está vacía, nadie es administrador.
    """
    raw_emails = os.environ.get(ADMIN_EMAILS_ENV, "")

    return {
        email.strip().lower()
        for email in raw_emails.split(",")
        if email.strip()
    }


def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.email.strip().lower() not in get_admin_emails():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción solo está disponible para administradores.",
        )

    return current_user


__all__ = ["get_current_user", "require_admin", "get_admin_emails"]
