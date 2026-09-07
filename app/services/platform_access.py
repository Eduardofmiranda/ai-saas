"""Autorização separada para operadores da plataforma.

Os papéis ``owner``, ``admin`` e ``agent`` continuam pertencendo à empresa.
Eles nunca concedem acesso cruzado entre empresas.
"""
from __future__ import annotations

from app.config import get_secret
from app.models.user import User


def is_platform_admin(user: User | None) -> bool:
    if not user:
        return False
    if bool(getattr(user, "is_platform_admin", False)):
        return True
    allowed = {
        email.strip().casefold()
        for email in get_secret("PLATFORM_ADMIN_EMAILS").split(",")
        if email.strip()
    }
    return user.email.casefold() in allowed