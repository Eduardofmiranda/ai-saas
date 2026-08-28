"""Criptografia de campos sensiveis (chaves de IA / Evolution) em repouso.

Valores sensiveis sao gravados no banco com o prefixo "enc:" seguido de um
token Fernet (AES-128-CBC + HMAC). A chave e derivada determinísticamente a
partir de `SECRET_ENCRYPTION_KEY` (ou, como fallback, `SECRET_KEY`) via PBKDF2.

Valores legados em texto puro continuam sendo lidos (compatibilidade), mas
sao re-criptografados no proximo save.
"""
from __future__ import annotations

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import get_secret

_PREFIX = "enc:"
_SALT = b"ai-saas-field-enc-v1"


def _fernet() -> Fernet:
    password = get_secret("SECRET_ENCRYPTION_KEY") or get_secret("SECRET_KEY", "dev-secret")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=200_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return Fernet(key)


def encrypt_field(value: str | None) -> str | None:
    """Criptografa um campo sensivel. Retorna None se vazio."""
    if not value:
        return value
    token = _fernet().encrypt(value.encode("utf-8"))
    return _PREFIX + token.decode("utf-8")


def decrypt_field(value: str | None) -> str | None:
    """Descriptografa um campo. Tolerante a valores em texto puro (legado)."""
    if not value:
        return value
    if value.startswith(_PREFIX):
        try:
            return _fernet().decrypt(value[len(_PREFIX):].encode("utf-8")).decode("utf-8")
        except Exception:
            return ""
    return value
